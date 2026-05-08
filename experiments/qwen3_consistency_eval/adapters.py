from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


@dataclass
class BenchmarkSpec:
    benchmark_id: str
    theme_id: str
    theme: str
    image_style_type: str
    expected_genre: str
    expected_tone: str
    must_have_constraints: list[str]
    forbidden_issues: list[str]

    def card(self) -> str:
        must = "\n".join(f"- {x}" for x in self.must_have_constraints if x)
        forbidden = "\n".join(f"- {x}" for x in self.forbidden_issues if x)
        return (
            f"Theme: {self.theme}\n"
            f"Expected genre: {self.expected_genre}\n"
            f"Expected tone: {self.expected_tone}\n"
            f"Image style: {self.image_style_type}\n"
            f"Must-have constraints:\n{must}\n"
            f"Forbidden issues:\n{forbidden}"
        )


@dataclass
class EvalSample:
    run_id: str
    system_name: str
    benchmark_id: str
    theme_id: str
    theme: str
    source_file: str
    generated_text: str
    turns: list[str]
    status: str = "pending"
    error: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


TEXT_KEYS = {
    "scene",
    "narrative_response",
    "world_basic_setting",
    "game_style",
    "main_quest",
    "protagonist_ability",
    "main_conflict",
    "conflict_end_condition",
    "summary",
    "content",
}


def split_pipe(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split("|") if x.strip()]


def load_benchmarks(path: Path) -> dict[str, BenchmarkSpec]:
    specs: dict[str, BenchmarkSpec] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            spec = BenchmarkSpec(
                benchmark_id=str(row.get("benchmark_id") or "").strip(),
                theme_id=str(row.get("theme_id") or "").strip(),
                theme=str(row.get("theme") or "").strip(),
                image_style_type=str(row.get("image_style_type") or "").strip(),
                expected_genre=str(row.get("expected_genre") or "").strip(),
                expected_tone=str(row.get("expected_tone") or "").strip(),
                must_have_constraints=split_pipe(row.get("must_have_constraints", "")),
                forbidden_issues=split_pipe(row.get("forbidden_issues", "")),
            )
            if spec.benchmark_id:
                specs[spec.benchmark_id] = spec
    return specs


def compact_text(parts: Iterable[str], max_chars: int = 12000) -> str:
    seen: set[str] = set()
    cleaned: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", str(part or "")).strip()
        if len(text) < 20 or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return "\n\n".join(cleaned)[:max_chars]


def get_path(obj: Any, path: list[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def flatten_core_worldview(worldview: dict[str, Any]) -> list[str]:
    core = get_path(worldview, ["response_json", "globalState", "core_worldview"]) or {}
    parts: list[str] = []
    if isinstance(core, dict):
        for key in ["world_basic_setting", "game_style", "main_quest", "protagonist_ability"]:
            if isinstance(core.get(key), str):
                parts.append(core[key])
        chapters = core.get("chapters")
        if isinstance(chapters, dict):
            for chapter in chapters.values():
                if isinstance(chapter, dict):
                    for key in ["main_conflict", "conflict_end_condition"]:
                        if isinstance(chapter.get(key), str):
                            parts.append(chapter[key])
    return parts


def standard_run_samples(root: Path, pattern: str, specs: dict[str, BenchmarkSpec]) -> list[EvalSample]:
    samples: list[EvalSample] = []
    for path in root.glob(pattern):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        runs = data.get("runs") if isinstance(data, dict) else None
        if not isinstance(runs, list):
            continue
        system = f"dn_{path.stem}"
        for idx, run in enumerate(runs):
            if not isinstance(run, dict):
                continue
            benchmark_id = str(run.get("benchmark_id") or "")
            spec = specs.get(benchmark_id)
            theme = str(run.get("theme") or (spec.theme if spec else ""))
            theme_id = str(run.get("theme_id") or (spec.theme_id if spec else ""))
            turns: list[str] = []
            parts: list[str] = []
            parts.extend(flatten_core_worldview(run.get("worldview") or {}))
            for click_key in ["first_click", "second_click"]:
                scene = get_path(run, [click_key, "response_json", "optionData", "scene"])
                recap = get_path(run, [click_key, "response_json", "optionData", "checkpoint_packet", "recap_text"])
                for text in [scene, recap]:
                    if isinstance(text, str):
                        turns.append(text)
                        parts.append(text)
            text = compact_text(parts)
            samples.append(EvalSample(
                run_id=f"{path.stem}:{idx}",
                system_name=system,
                benchmark_id=benchmark_id,
                theme_id=theme_id,
                theme=theme,
                source_file=str(path),
                generated_text=text,
                turns=turns,
                status="ok" if text else "missing_raw_text",
                error="" if text else "No generated text found in standard run.",
            ))
    return samples


def rolling_baseline_samples(root: Path, pattern: str, specs: dict[str, BenchmarkSpec]) -> list[EvalSample]:
    samples: list[EvalSample] = []
    for theme_dir in root.glob(pattern):
        if not theme_dir.is_dir():
            continue
        seg_dir = theme_dir / "segments"
        segments: list[tuple[int, str]] = []
        meta_theme = ""
        theme_id = ""
        for seg_path in sorted(seg_dir.glob("*.json")):
            try:
                obj = json.loads(seg_path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            scene = obj.get("scene") if isinstance(obj, dict) else None
            if isinstance(scene, str):
                segments.append((int(obj.get("segment_index") or len(segments) + 1), scene))
            meta_theme = str(obj.get("theme") or meta_theme)
            theme_id = str(obj.get("theme_item_id") or theme_id)
        spec = next((s for s in specs.values() if s.theme_id == theme_id or s.theme == meta_theme), None)
        text = compact_text([x[1] for x in segments])
        samples.append(EvalSample(
            run_id=theme_dir.name,
            system_name="baseline_text_rolling_4o",
            benchmark_id=spec.benchmark_id if spec else "",
            theme_id=theme_id or (spec.theme_id if spec else ""),
            theme=meta_theme or (spec.theme if spec else ""),
            source_file=str(theme_dir),
            generated_text=text,
            turns=[x[1] for x in segments],
            status="ok" if text else "missing_raw_text",
            error="" if text else "No segment scene text found.",
        ))
    return samples


def normalized_baseline_samples(root: Path, pattern: str, specs: dict[str, BenchmarkSpec]) -> list[EvalSample]:
    samples: list[EvalSample] = []
    for path in root.glob(pattern):
        if path.name in {"summary.json"}:
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        baseline_id = str(obj.get("baseline_id") or path.parent.name)
        benchmark_id = str(obj.get("benchmark_id") or "")
        input_bundle = obj.get("input_bundle") if isinstance(obj.get("input_bundle"), dict) else {}
        theme = str(input_bundle.get("theme") or input_bundle.get("premise_seed") or "")
        theme_id = str(input_bundle.get("theme_id") or "")
        spec = specs.get(benchmark_id) or next((s for s in specs.values() if s.theme == theme or s.theme_id == theme_id), None)
        parts: list[str] = []
        normalized = obj.get("normalized_response")
        if isinstance(normalized, dict):
            for key in ["narrative_response", "scene_setup", "player_state"]:
                if isinstance(normalized.get(key), str):
                    parts.append(normalized[key])
        raw_content = get_path(obj, ["raw_output", "response", "choices"])
        if isinstance(raw_content, list):
            for choice in raw_content[:1]:
                content = get_path(choice, ["message", "content"])
                if isinstance(content, str):
                    parts.append(content)
        text = compact_text(parts)
        samples.append(EvalSample(
            run_id=str(obj.get("run_id") or path.stem),
            system_name=f"baseline_{baseline_id}",
            benchmark_id=benchmark_id or (spec.benchmark_id if spec else ""),
            theme_id=theme_id or (spec.theme_id if spec else ""),
            theme=theme or (spec.theme if spec else ""),
            source_file=str(path),
            generated_text=text,
            turns=parts,
            status="ok" if text else "missing_raw_text",
            error="" if text else "No normalized/raw response text found.",
        ))
    return samples


def collect_missing_summary_files(root: Path, patterns: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.suffix.lower() not in {".csv", ".json"}:
                continue
            rows.append({
                "source_file": str(path),
                "status": "not_ingested",
                "error": "Summary or metric table; raw generated text not reliably available.",
            })
    return rows


def load_all_samples(root: Path, config: dict[str, Any], specs: dict[str, BenchmarkSpec]) -> tuple[list[EvalSample], list[dict[str, Any]]]:
    inputs = config["inputs"]
    samples: list[EvalSample] = []
    samples.extend(standard_run_samples(root, inputs["standard_runs_glob"], specs))
    samples.extend(rolling_baseline_samples(root, inputs["rolling_baseline_glob"], specs))
    samples.extend(normalized_baseline_samples(root, inputs["normalized_baseline_glob"], specs))
    missing = collect_missing_summary_files(root, inputs.get("summary_globs", []))
    # De-duplicate by system/run/source.
    unique: dict[tuple[str, str, str], EvalSample] = {}
    for sample in samples:
        key = (sample.system_name, sample.run_id, sample.source_file)
        unique[key] = sample
    return list(unique.values()), missing

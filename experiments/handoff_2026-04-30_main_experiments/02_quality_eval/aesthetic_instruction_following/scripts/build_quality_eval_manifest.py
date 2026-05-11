# -*- coding: utf-8 -*-
"""Build the formal20 visual-quality manifest for aesthetic consistency and instruction following."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

REPO_ROOT = Path(__file__).resolve().parents[5]
OUT_DIR = Path(__file__).resolve().parents[1] / "results"

BENCHMARK_PATH = REPO_ROOT / "experiments/benchmark/dn_quality_benchmark_v1.json"
DN_Pregen_PATH = REPO_ROOT / "experiments/benchmark/standard_runs/benchmark_v15_fullready_nextturn_pregen60s20_composite20_v1.json"
DN_TABLE_PATH = REPO_ROOT / "experiments/benchmark/standard_runs/benchmark_v15_fullready_nextturn_20_table_composite20_v1.csv"
REMOTE_OUT = REPO_ROOT / "remote_baseline_results_20260430/outputs"

MANIFEST_PATH = OUT_DIR / "quality_eval_manifest_formal20_v1.jsonl"
MISSING_PATH = OUT_DIR / "missing_or_invalid_images.csv"
GROUPS_PATH = OUT_DIR / "quality_eval_groups_formal20_v1.json"
SUMMARY_PATH = OUT_DIR / "manifest_coverage_summary.json"
HUMAN_TEMPLATE_PATH = OUT_DIR / "human_rating_template_formal20_v1.csv"

SYSTEM_OUTPUT_SCOPE = {
    "DN": "full-ready story scene image",
    "StoryDiffusion": "image-continuation reference",
    "SDM-v2": "image-continuation reference",
    "IC-LoRA": "image-continuation workflow reference",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def is_valid_image(path: Optional[Path]) -> bool:
    if path is None or not path.is_file():
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except (OSError, UnidentifiedImageError):
        return False


def resolve_dn_image(url_or_path: str) -> Optional[Path]:
    if not url_or_path:
        return None
    value = url_or_path.strip()
    if value.startswith("/image_cache/"):
        candidate = REPO_ROOT / value.lstrip("/")
    else:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
    return candidate if candidate.is_file() else None


def map_remote_image_path(remote_path: str, result_json: Path) -> Optional[Path]:
    """Map /root/autodl-tmp/outputs/... or ComfyUI output paths to local result folders."""
    if not remote_path:
        return None
    name = Path(remote_path).name
    direct = result_json.parent / name
    if direct.is_file():
        return direct
    # Some baseline records contain nested or absolute Linux paths. Prefer basename under the sample folder.
    matches = list(result_json.parent.glob(name))
    if matches:
        return matches[0]
    return None


def benchmark_items() -> Dict[str, Dict[str, Any]]:
    data = load_json(BENCHMARK_PATH)
    items = {item["benchmark_id"]: item for item in data["items"]}
    # The benchmark JSON in this snapshot contains mojibake in some Chinese fields.
    # The formal20 table preserves readable theme names, so use it when available.
    if DN_TABLE_PATH.is_file():
        with DN_TABLE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                bid = row.get("benchmark_id", "")
                theme = row.get("theme", "")
                if bid in items and theme:
                    items[bid]["theme"] = theme
    return items


def item_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "theme": item.get("theme", ""),
        "expected_genre": item.get("expected_genre", ""),
        "expected_tone": item.get("expected_tone", ""),
        "image_style": item.get("image_style", {}),
        "must_have_constraints": item.get("must_have_constraints", []),
        "forbidden_issues": item.get("forbidden_issues", []),
    }


def make_record(
    *,
    system: str,
    benchmark_id: str,
    turn_type: str,
    image_path: Optional[Path],
    scene_text: str,
    generation_prompt: str,
    source_json: Path,
    item: Dict[str, Any],
    missing: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    if not is_valid_image(image_path):
        missing.append({
            "system": system,
            "benchmark_id": benchmark_id,
            "turn_type": turn_type,
            "reason": "image_path_missing_unreadable_or_invalid",
            "source_json": repo_rel(source_json),
            "image_path": "" if image_path is None else str(image_path),
        })
        return None
    fields = item_fields(item)
    sample_id = f"{system.lower().replace('-', '').replace(' ', '')}_{benchmark_id}_{turn_type}"
    return {
        "sample_id": sample_id,
        "system": system,
        "output_scope": SYSTEM_OUTPUT_SCOPE[system],
        "benchmark_id": benchmark_id,
        "theme_id": item.get("theme_id"),
        "turn_type": turn_type,
        "image_path": repo_rel(image_path),
        "source_json": repo_rel(source_json),
        "scene_text": scene_text or "",
        "generation_prompt": generation_prompt or "",
        **fields,
    }


def build_dn_records(items: Dict[str, Dict[str, Any]], missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    data = load_json(DN_Pregen_PATH)
    records: List[Dict[str, Any]] = []
    for run in data.get("runs", []):
        bid = run.get("benchmark_id")
        if bid not in items:
            continue
        item = items[bid]
        source_json = DN_Pregen_PATH

        first_option = run.get("first_click", {}).get("response_json", {}).get("optionData", {})
        first_img = first_option.get("scene_image", {}) or {}
        records.append(make_record(
            system="DN",
            benchmark_id=bid,
            turn_type="first_turn",
            image_path=resolve_dn_image(first_img.get("url", "")),
            scene_text=first_option.get("scene", ""),
            generation_prompt=first_img.get("prompt", ""),
            source_json=source_json,
            item=item,
            missing=missing,
        ))

        prev_img = run.get("second_click", {}).get("request_payload", {}).get("previousSceneImage", {}) or {}
        records.append(make_record(
            system="DN",
            benchmark_id=bid,
            turn_type="next_turn_current",
            image_path=resolve_dn_image(prev_img.get("url", "")),
            scene_text=run.get("second_click", {}).get("request_payload", {}).get("previousSceneText", ""),
            generation_prompt=prev_img.get("prompt", ""),
            source_json=source_json,
            item=item,
            missing=missing,
        ))

        second_option = run.get("second_click", {}).get("response_json", {}).get("optionData", {})
        second_img = (run.get("full_ready", {}).get("image_probe", {}).get("image") or second_option.get("scene_image", {}) or {})
        records.append(make_record(
            system="DN",
            benchmark_id=bid,
            turn_type="next_turn_next",
            image_path=resolve_dn_image(second_img.get("url", "")),
            scene_text=second_option.get("scene", ""),
            generation_prompt=second_img.get("prompt", ""),
            source_json=source_json,
            item=item,
            missing=missing,
        ))
    return [r for r in records if r is not None]


def baseline_result(system: str, mode: str, bid: str) -> Optional[Path]:
    patterns = {
        ("StoryDiffusion", "first_turn"): "storydiffusion_formal20/*/{}*/result.json",
        ("StoryDiffusion", "next_turn"): "storydiffusion_nextturn_formal20/*/{}/result.json",
        ("SDM-v2", "first_turn"): "sdmv2_local_formal20/*/{}/result.json",
        ("SDM-v2", "next_turn"): "sdmv2_nextturn_formal20/*/{}/result.json",
        ("IC-LoRA", "first_turn"): "iclora_formal20_real/*/{}/result.json",
        ("IC-LoRA", "next_turn"): "iclora_nextturn_formal20_real/*/{}/result.json",
    }
    pat = patterns[(system, mode)].format(bid)
    matches = sorted(REMOTE_OUT.glob(pat))
    return matches[0] if matches else None


def prompt_from(data: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        cur: Any = data
        ok = True
        for part in k.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()
    return ""


def image_for_baseline(data: Dict[str, Any], source_json: Path, turn_type: str, system: str) -> Optional[Path]:
    paths = data.get("image_paths") or data.get("image_artifacts") or []
    if not isinstance(paths, list):
        paths = []
    if turn_type == "first_turn":
        if system == "StoryDiffusion" and len(paths) >= 4:
            return map_remote_image_path(paths[3], source_json)
        return map_remote_image_path(paths[0], source_json) if paths else None
    if turn_type == "next_turn_current":
        if system == "StoryDiffusion":
            preferred = source_json.parent / "current_image_002.png"
        elif system == "SDM-v2":
            preferred = source_json.parent / "current_image_001.png"
        else:
            matches = sorted(source_json.parent.glob("ICLORA_CURRENT_*.png"))
            return matches[0] if matches else None
        return preferred if preferred.is_file() else None
    if turn_type == "next_turn_next":
        if system == "IC-LoRA":
            matches = sorted(source_json.parent.glob("ICLORA_NEXT_*.png"))
            return matches[0] if matches else None
        return map_remote_image_path(paths[0], source_json) if paths else None
    return None


def build_baseline_records(items: Dict[str, Dict[str, Any]], missing: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for system in ["StoryDiffusion", "SDM-v2", "IC-LoRA"]:
        for bid, item in items.items():
            first_json = baseline_result(system, "first_turn", bid)
            next_json = baseline_result(system, "next_turn", bid)
            if first_json is not None:
                data = load_json(first_json)
                prompt = prompt_from(data, "raw_output.prompt", "prompt", "input_bundle.prompt_pack.prompts.0")
                records.append(make_record(
                    system=system,
                    benchmark_id=bid,
                    turn_type="first_turn",
                    image_path=image_for_baseline(data, first_json, "first_turn", system),
                    scene_text=prompt,
                    generation_prompt=prompt,
                    source_json=first_json,
                    item=item,
                    missing=missing,
                ))
            else:
                missing.append({"system": system, "benchmark_id": bid, "turn_type": "first_turn", "reason": "result_json_missing", "source_json": "", "image_path": ""})

            if next_json is not None:
                data = load_json(next_json)
                current_prompt = prompt_from(data, "raw_output.current_prompt", "input_bundle.prompt_pack.prompts.0")
                next_prompt = prompt_from(data, "input_bundle.next_turn_prompt", "raw_output.continuation_prompt", "prompt_list.0")
                for turn_type, text in [("next_turn_current", current_prompt), ("next_turn_next", next_prompt)]:
                    records.append(make_record(
                        system=system,
                        benchmark_id=bid,
                        turn_type=turn_type,
                        image_path=image_for_baseline(data, next_json, turn_type, system),
                        scene_text=text,
                        generation_prompt=text,
                        source_json=next_json,
                        item=item,
                        missing=missing,
                    ))
            else:
                for tt in ["next_turn_current", "next_turn_next"]:
                    missing.append({"system": system, "benchmark_id": bid, "turn_type": tt, "reason": "result_json_missing", "source_json": "", "image_path": ""})
    return [r for r in records if r is not None]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = benchmark_items()
    missing: List[Dict[str, str]] = []
    records = build_dn_records(items, missing) + build_baseline_records(items, missing)
    records = sorted(records, key=lambda r: (r["system"], r["benchmark_id"], r["turn_type"]))

    write_jsonl(MANIFEST_PATH, records)
    write_csv(MISSING_PATH, missing, ["system", "benchmark_id", "turn_type", "reason", "source_json", "image_path"])

    groups: Dict[str, List[str]] = {}
    for rec in records:
        key = f"{rec['system']}::{rec['benchmark_id']}"
        groups.setdefault(key, []).append(rec["sample_id"])
    GROUPS_PATH.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")

    by_system: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        d = by_system.setdefault(rec["system"], {"image_records": 0, "benchmark_ids": set(), "turn_types": set()})
        d["image_records"] += 1
        d["benchmark_ids"].add(rec["benchmark_id"])
        d["turn_types"].add(rec["turn_type"])
    summary = {
        "manifest_path": repo_rel(MANIFEST_PATH),
        "missing_path": repo_rel(MISSING_PATH),
        "group_count": len(groups),
        "image_record_count": len(records),
        "missing_count": len(missing),
        "systems": {
            k: {
                "image_records": v["image_records"],
                "benchmark_count": len(v["benchmark_ids"]),
                "turn_types": sorted(v["turn_types"]),
            }
            for k, v in sorted(by_system.items())
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    human_fields = [
        "sample_id", "system", "benchmark_id", "turn_type", "image_path", "theme", "image_style",
        "instruction_following_score", "theme_alignment", "text_image_alignment", "style_following",
        "constraint_coverage", "forbidden_violation", "aesthetic_consistency_score", "style_lighting_consistency",
        "subject_attribute_consistency", "scene_world_consistency", "composition_quality", "artifact_rate", "reason", "failure_tags",
    ]
    template_rows = []
    for rec in records:
        row = {k: rec.get(k, "") for k in human_fields}
        row["image_style"] = json.dumps(rec.get("image_style", {}), ensure_ascii=False)
        template_rows.append(row)
    write_csv(HUMAN_TEMPLATE_PATH, template_rows, human_fields)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())

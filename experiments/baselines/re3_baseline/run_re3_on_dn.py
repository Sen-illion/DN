# -*- coding: utf-8 -*-
"""Run Re3 story generation on DN themes and export DN evaluator format.

This is an adapter around the upstream Re3 CLI. It keeps Re3 as the generator,
then converts each generated story into the same manifest/segment layout used
by DN's text-coherence evaluator.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RE3_ROOT = REPO_ROOT / "external" / "re3-story-generation"
DEFAULT_THEMES_FILE = REPO_ROOT / "game_themes_100.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "experiments" / "baselines" / "text_re3"
DEFAULT_THEME_IDS = "1,2,3,4,5,6,12,18,54,73"


STYLE_HINTS = {
    "realistic": "realistic visual style with credible details and grounded motives",
    "cyberpunk": "cyberpunk style with neon technology, social conflict, and noir tension",
    "ink_painting": "Chinese ink-painting mood with restraint, poetic imagery, and negative space",
    "watercolor": "watercolor style with soft colors, transparent layers, and emotional clarity",
    "anime": "anime style with expressive characters, strong emotions, and dynamic scenes",
    "oil_painting": "oil-painting style with dramatic light, texture, and classical composition",
}


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def first_env(keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value.strip()
    return default


def parse_theme_ids(raw: str) -> List[int]:
    values: List[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            values.extend(range(int(left), int(right) + 1))
        else:
            values.append(int(part))
    return values


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return slug.strip("_")[:48] or "theme"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_themes(path: Path, theme_ids: List[int], max_themes: int) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = [item for item in data.get("items", []) if isinstance(item, dict)]
    if theme_ids:
        wanted = set(theme_ids)
        items = [item for item in items if int(item.get("id", -1)) in wanted]
    items.sort(key=lambda item: int(item.get("id", 0)))
    if max_themes > 0:
        items = items[:max_themes]
    return items


def style_prompt(item: Dict[str, Any]) -> str:
    style = item.get("image_style") or {}
    style_type = style.get("type", "") if isinstance(style, dict) else ""
    subtype = style.get("subtype", "") if isinstance(style, dict) else ""
    label = item.get("style_label_zh") or style_type or "unspecified style"
    hint = STYLE_HINTS.get(style_type, "stable story and visual style")
    if subtype:
        hint += f"; subtype: {subtype}"
    return f"{label} / {style_type}. {hint}."


def build_premise(item: Dict[str, Any], language: str) -> str:
    theme = str(item.get("theme", "")).strip()
    style = style_prompt(item)
    if language == "zh":
        return (
            f"请写一个中文长篇游戏剧情故事，主题是：{theme}。"
            f"视觉和叙事风格：{style} "
            "故事应有稳定主角、明确目标、持续冲突、因果推进和完整结局。"
        )
    return (
        f"Write a long-form game narrative story in Chinese based on this theme: {theme}. "
        f"Style: {style} "
        "The story should keep a stable protagonist, a clear goal, persistent conflict, "
        "causal progression, and a complete ending."
    )


def split_story(story_text: str, segments: int) -> List[str]:
    story_text = re.sub(r"\s+\n", "\n", story_text.strip())
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", story_text) if p.strip()]
    if len(paragraphs) >= segments:
        buckets = [[] for _ in range(segments)]
        for idx, paragraph in enumerate(paragraphs):
            buckets[min(idx * segments // len(paragraphs), segments - 1)].append(paragraph)
        return ["\n\n".join(bucket).strip() for bucket in buckets if bucket]

    # Re3 sometimes returns one long paragraph. Fall back to approximate
    # character-balanced chunks while preserving sentence boundaries when possible.
    sentences = re.split(r"(?<=[。！？.!?])\s+", story_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [story_text]
    target = max(1, len(story_text) // segments)
    parts: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for sentence in sentences:
        cur.append(sentence)
        cur_len += len(sentence)
        if cur_len >= target and len(parts) < segments - 1:
            parts.append(" ".join(cur).strip())
            cur = []
            cur_len = 0
    if cur:
        parts.append(" ".join(cur).strip())
    return [p for p in parts if p]


def export_dn_layout(
    out_dir: Path,
    game_id: str,
    theme_id: int,
    theme: str,
    story_text: str,
    segments: int,
    artifacts: Dict[str, str],
) -> None:
    parts = split_story(story_text, segments)
    seg_dir = out_dir / "segments"
    manifest_segments = []
    for i, scene in enumerate(parts, start=1):
        name = f"{i:03d}.json"
        write_json(
            seg_dir / name,
            {
                "scene": scene,
                "theme_item_id": theme_id,
                "baseline": "Re3",
                "source": "emnlp22-re3-story-generation",
            },
        )
        manifest_segments.append({"index": i, "json": f"segments/{name}"})

    write_json(
        out_dir / f"{game_id}_manifest.json",
        {
            "game_id": game_id,
            "theme_item_id": theme_id,
            "theme": theme,
            "segment_count": len(parts),
            "text_only": True,
            "baseline": "Re3",
            "artifacts": artifacts,
            "segments": manifest_segments,
        },
    )


def default_re3_python(re3_root: Path) -> Path:
    venv_python = re3_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return venv_python
    return Path(sys.executable)


def find_re3_data(re3_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    candidates = [
        re3_root / "emnlp22_re3_data",
        REPO_ROOT / "external" / "emnlp22_re3_data",
        REPO_ROOT / "emnlp22_re3_data",
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return candidates[0]


def extract_story_with_re3_python(re3_python: Path, re3_root: Path, complete_pkl: Path, story_txt: Path) -> None:
    helper = story_txt.parent / "_extract_re3_story.py"
    helper.write_text(
        "\n".join(
            [
                "import pickle, sys",
                "from pathlib import Path",
                "re3_root = Path(sys.argv[1])",
                "complete_pkl = Path(sys.argv[2])",
                "story_txt = Path(sys.argv[3])",
                "sys.path.insert(0, str(re3_root))",
                "with complete_pkl.open('rb') as f:",
                "    beam = pickle.load(f)",
                "story = beam[0].story() if isinstance(beam, list) else beam.story()",
                "story_txt.write_text(story.strip(), encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [str(re3_python), str(helper), str(re3_root), str(complete_pkl), str(story_txt)],
        check=True,
    )


def parse_story_from_log(log_path: Path) -> str:
    if not log_path.is_file():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    marker = "FINAL STORY"
    idx = text.rfind(marker)
    if idx == -1:
        return ""
    return text[idx + len(marker) :].strip()


def build_re3_command(
    args: argparse.Namespace,
    re3_data: Path,
    premise: str,
    outline_pkl: Path,
    complete_pkl: Path,
    log_file: Path,
) -> List[str]:
    rel_ckpt = re3_data / "ckpt" / "relevance_reranker"
    coh_ckpt = re3_data / "ckpt" / "coherence_reranker"
    cmd = [
        str(args.re3_python),
        "-u",
        str(args.re3_root / "scripts" / "main.py"),
        "--premise",
        premise,
        "--summarizer",
        "gpt3_summarizer",
        "--controller",
        "longformer_classifier",
        "longformer_classifier",
        "--loader",
        "alignment",
        "coherence",
        "--controller-load-dir",
        str(rel_ckpt),
        str(coh_ckpt),
        "--controller-model-string",
        "allenai/longformer-base-4096",
        "allenai/longformer-base-4096",
        "--gpt3-model",
        args.gpt3_model,
        "--plan-model-string",
        args.plan_model,
        "--draft-model-string",
        args.draft_model,
        "--save-outline-file",
        str(outline_pkl),
        "--save-complete-file",
        str(complete_pkl),
        "--log-file",
        str(log_file),
        "--fixed-outline-length",
        str(args.fixed_outline_length),
        "--outline-levels",
        str(args.outline_levels),
        "--max-continuation-substeps",
        str(args.max_continuation_substeps),
        "--generation-max-length",
        str(args.generation_max_length),
        "--max-candidates",
        str(args.max_candidates),
        "--log-level",
        str(args.log_level),
    ]
    if args.no_editor:
        cmd.append("--no-editor")
    if args.cut_sentence:
        cmd.append("--cut-sentence")
    return cmd


def run_one_theme(args: argparse.Namespace, re3_data: Path, env: Dict[str, str], item: Dict[str, Any]) -> Dict[str, Any]:
    theme_id = int(item["id"])
    theme = str(item.get("theme", "")).strip()
    game_id = f"re3_theme_{theme_id:03d}"
    out_dir = args.output_root / f"theme_{theme_id:03d}_{safe_slug(theme)}"
    artifact_dir = out_dir / "re3_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / f"{game_id}_manifest.json"
    if manifest_path.is_file() and args.resume and not args.overwrite:
        return {"theme_id": theme_id, "theme": theme, "status": "skipped_existing", "out_dir": str(out_dir)}

    premise = build_premise(item, args.premise_language)
    premise_path = artifact_dir / "premise.txt"
    outline_pkl = artifact_dir / "outline.pkl"
    complete_pkl = artifact_dir / "complete_story.pkl"
    log_file = artifact_dir / "story.log"
    story_txt = artifact_dir / "story.txt"

    premise_path.write_text(premise, encoding="utf-8")
    cmd = build_re3_command(args, re3_data, premise, outline_pkl, complete_pkl, log_file)
    write_json(artifact_dir / "command.json", {"cmd": cmd, "cwd": str(args.re3_root)})

    if args.dry_run:
        return {"theme_id": theme_id, "theme": theme, "status": "dry_run", "cmd": cmd, "out_dir": str(out_dir)}

    if args.overwrite:
        for p in [outline_pkl, complete_pkl, story_txt, log_file]:
            if p.exists():
                p.unlink()

    started = time.time()
    subprocess.run(cmd, cwd=str(args.re3_root), env=env, check=True)
    elapsed = time.time() - started

    story = ""
    if complete_pkl.is_file():
        try:
            extract_story_with_re3_python(args.re3_python, args.re3_root, complete_pkl, story_txt)
            story = story_txt.read_text(encoding="utf-8").strip()
        except Exception as exc:  # noqa: BLE001 - keep log fallback for old pickle/import issues
            (artifact_dir / "extract_error.txt").write_text(str(exc), encoding="utf-8")

    if not story:
        story = parse_story_from_log(log_file)
        if story:
            story_txt.write_text(story, encoding="utf-8")
    if not story:
        raise RuntimeError(f"Re3 finished but no story could be extracted for theme {theme_id}")

    export_dn_layout(
        out_dir,
        game_id,
        theme_id,
        theme,
        story,
        args.segments,
        {
            "premise": str(premise_path),
            "outline_pkl": str(outline_pkl),
            "complete_pkl": str(complete_pkl),
            "log": str(log_file),
            "story_txt": str(story_txt),
        },
    )
    return {
        "theme_id": theme_id,
        "theme": theme,
        "status": "ok",
        "out_dir": str(out_dir),
        "story_chars": len(story),
        "elapsed_seconds": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Re3 on DN game themes and export DN evaluator layout.")
    parser.add_argument("--re3-root", type=Path, default=DEFAULT_RE3_ROOT)
    parser.add_argument("--re3-python", type=Path, default=None)
    parser.add_argument("--re3-data-root", type=Path, default=None)
    parser.add_argument("--themes-file", type=Path, default=DEFAULT_THEMES_FILE)
    parser.add_argument("--theme-ids", default=DEFAULT_THEME_IDS)
    parser.add_argument("--max-themes", type=int, default=0)
    parser.add_argument("--segments", type=int, default=10)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--premise-language", choices=["en", "zh"], default="en")
    parser.add_argument("--gpt3-model", default=first_env(["RE3_GPT3_MODEL"], "text-davinci-002"))
    parser.add_argument("--plan-model", default=first_env(["RE3_PLAN_MODEL"], "text-davinci-002"))
    parser.add_argument("--draft-model", default=first_env(["RE3_DRAFT_MODEL"], "davinci"))
    parser.add_argument("--fixed-outline-length", type=int, default=3)
    parser.add_argument("--outline-levels", type=int, default=1)
    parser.add_argument("--max-continuation-substeps", type=int, default=4)
    parser.add_argument("--generation-max-length", type=int, default=256)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--log-level", type=int, default=22)
    parser.add_argument("--no-editor", action="store_true", help="Use the faster Plan-Draft-Rewrite ablation.")
    parser.add_argument("--cut-sentence", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    args.re3_root = args.re3_root.resolve()
    args.re3_python = (args.re3_python or default_re3_python(args.re3_root)).resolve()
    args.re3_data_root = find_re3_data(args.re3_root, args.re3_data_root).resolve()
    args.output_root = args.output_root.resolve()

    if not (args.re3_root / "scripts" / "main.py").is_file():
        raise SystemExit(f"Re3 scripts/main.py not found: {args.re3_root}")
    if not args.re3_python.is_file():
        raise SystemExit(f"Re3 Python not found: {args.re3_python}")
    if not (args.re3_data_root / "ckpt" / "relevance_reranker").is_dir():
        raise SystemExit(
            "Missing Re3 data/ckpts. Download and unzip emnlp22_re3_data, then pass "
            f"--re3-data-root. Tried: {args.re3_data_root}"
        )

    env = os.environ.copy()
    api_key = first_env(["RE3_OPENAI_API_KEY", "OPENAI_API_KEY", "YUNWU_API_KEY", "COHERENCE_API_KEY"])
    api_base = first_env(["RE3_OPENAI_API_BASE", "OPENAI_API_BASE", "OPENAI_BASE_URL", "YUNWU_BASE_URL", "COHERENCE_BASE_URL"])
    if api_key:
        env["OPENAI_API_KEY"] = api_key
    if api_base:
        # Old openai==0.16 reads api_base, commonly configured via OPENAI_API_BASE.
        env["OPENAI_API_BASE"] = api_base
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")

    themes = load_themes(args.themes_file, parse_theme_ids(args.theme_ids), args.max_themes)
    if not themes:
        raise SystemExit("No themes selected.")

    args.output_root.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for item in themes:
        result = run_one_theme(args, args.re3_data_root, env, item)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    write_json(
        args.output_root / "run_meta.json",
        {
            "baseline": "Re3",
            "re3_root": str(args.re3_root),
            "re3_python": str(args.re3_python),
            "re3_data_root": str(args.re3_data_root),
            "themes_file": str(args.themes_file.resolve()),
            "theme_ids": args.theme_ids,
            "segments": args.segments,
            "results": results,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

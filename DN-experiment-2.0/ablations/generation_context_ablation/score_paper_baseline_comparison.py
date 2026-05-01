from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

from openpyxl import Workbook

THIS_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = THIS_DIR.parents[1]
REPO_ROOT = THIS_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")

from common import as_text, discover_source_games, load_json, write_json, write_jsonl


SCORE_SCRIPT_PATH = (
    EXPERIMENT_ROOT
    / "图片一致性_experiment"
    / "multiview_image_consistency"
    / "scripts"
    / "score_image_consistency_per_game.py"
)


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def ensure_openai_env() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        for key in ("COHERENCE_API_KEY", "VISION_REF_API_KEY", "Origin_Segment_Analyst_API_KEY", "Camera_Analyst_API_KEY"):
            if os.getenv(key):
                os.environ["OPENAI_API_KEY"] = os.getenv(key, "")
                break
    if not os.getenv("OPENAI_BASE_URL"):
        for key in ("COHERENCE_BASE_URL", "VISION_REF_BASE_URL", "Origin_Segment_Analyst_BASE_URL", "Camera_Analyst_BASE_URL"):
            if os.getenv(key):
                os.environ["OPENAI_BASE_URL"] = os.getenv(key, "")
                break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score DN vs paper image-consistency baselines.")
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--models", default="gpt-4o")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def parse_models(raw: str) -> List[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def append_sheet(workbook: Workbook, title: str, rows: List[Dict[str, Any]]) -> None:
    ws = workbook.create_sheet(title=title)
    if not rows:
        ws.append(["empty"])
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([json.dumps(row.get(h), ensure_ascii=False) if isinstance(row.get(h), (dict, list)) else row.get(h, "") for h in headers])


def build_samples(manifest: Dict[str, Any], run_dir: Path, scoring_module) -> List[Dict[str, Any]]:
    games = {game.game_id: game for game in discover_source_games()}
    wanted: Dict[str, Dict[str, Any]] = {}
    for task in manifest.get("tasks", []):
        if int(task.get("segment_index", 0)) == 2:
            wanted[as_text(task.get("game_id"))] = task

    samples: List[Dict[str, Any]] = []
    groups = ["dn_ours", "naive_t2i", "prompt_only_memory", "visual_bible", "prompt_plus_prev_image"]
    for game_id, task in sorted(wanted.items(), key=lambda item: int(item[1].get("theme_id", 0))):
        source_game = games.get(game_id)
        if source_game is None:
            continue
        current_source = source_game.segments.get(2)
        previous_source = source_game.segments.get(1)
        if current_source is None:
            continue
        for group in groups:
            if group == "dn_ours":
                image_path = current_source.image_path
                prev_image_path = previous_source.image_path if previous_source else None
                prompt_text = current_source.prompt
                scene_text = current_source.scene
            else:
                image_path = run_dir / "generated" / group / game_id / "seg_002.png"
                prev_image_path = run_dir / "generated" / group / game_id / "seg_001.png"
                json_path = run_dir / "generated" / group / game_id / "seg_002.json"
                payload = load_json(json_path) if json_path.is_file() else {}
                prompt_text = as_text((payload.get("image_result") or {}).get("prompt") or payload.get("source_prompt") or current_source.prompt)
                scene_text = as_text(payload.get("source_scene") or current_source.scene)
            if image_path is None or not Path(image_path).is_file():
                samples.append(
                    {
                        "group": group,
                        "theme_id": task.get("theme_id"),
                        "theme": task.get("theme"),
                        "game_id": game_id,
                        "segment_index": 2,
                        "sample_id": f"{group}__{game_id}_seg_002",
                        "status": "missing_image",
                        "image_path": str(image_path or ""),
                    }
                )
                continue
            sample = scoring_module.Sample(
                game_id=game_id,
                theme_item_id=task.get("theme_id"),
                segment_index=2,
                sample_id=f"{group}__{game_id}_seg_002",
                image_path=Path(image_path),
                prompt_text=prompt_text,
                scene_text=scene_text,
                prev_image_path=Path(prev_image_path) if prev_image_path and Path(prev_image_path).is_file() else None,
                prev_scene_text=previous_source.scene if previous_source else "",
            )
            samples.append(
                {
                    "group": group,
                    "theme_id": task.get("theme_id"),
                    "theme": task.get("theme"),
                    "game_id": game_id,
                    "segment_index": 2,
                    "sample_id": sample.sample_id,
                    "status": "ready",
                    "image_path": str(sample.image_path),
                    "sample": sample,
                }
            )
    return samples


def summarize(rows: List[Dict[str, Any]], missing_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups = ["dn_ours", "naive_t2i", "prompt_only_memory", "visual_bible", "prompt_plus_prev_image"]
    out: List[Dict[str, Any]] = []
    for group in groups:
        vals = [row for row in rows if row.get("group") == group]
        missing = [row for row in missing_rows if row.get("group") == group]
        planned = len(vals) + len(missing)
        item: Dict[str, Any] = {
            "group": group,
            "planned_samples": planned,
            "scored_samples": len(vals),
            "missing_samples": len(missing),
            "coverage": round(len(vals) / planned, 4) if planned else 0.0,
        }
        metrics = ["overall_score", "semantic_consistency", "subject_attribute_consistency", "spatial_consistency", "style_lighting_consistency", "detail_integrity", "confidence"]
        for metric in metrics:
            item[f"{metric}_mean"] = round(mean([float(row[metric]) for row in vals]), 4) if vals else None
        out.append(item)
    base = next((row for row in out if row["group"] == "dn_ours"), None)
    base_score = base.get("overall_score_mean") if base else None
    for item in out:
        item["delta_vs_dn_ours"] = round(float(item["overall_score_mean"]) - float(base_score), 4) if item.get("overall_score_mean") is not None and base_score is not None else None
    return out


def main() -> int:
    args = parse_args()
    ensure_openai_env()
    scoring_module = load_module("paper_baseline_score_module", SCORE_SCRIPT_PATH)
    scoring_module.load_env()
    ensure_openai_env()
    models = parse_models(args.models)
    if not models:
        raise RuntimeError("No judge model provided.")
    client = scoring_module.OpenAI()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(args.dataset_manifest)
    sample_entries = build_samples(manifest, args.run_dir, scoring_module)
    raw_path = args.output_dir / "per_sample_scores.jsonl"
    existing: Dict[str, Dict[str, Any]] = {}
    if args.resume and raw_path.is_file():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing[f"{row.get('sample_id')}::{row.get('judge_model')}"] = row

    rows = list(existing.values())
    missing_rows = [{k: v for k, v in entry.items() if k != "sample"} for entry in sample_entries if entry["status"] != "ready"]
    for entry in sample_entries:
        if entry["status"] != "ready":
            continue
        sample = entry["sample"]
        for model in models:
            key = f"{sample.sample_id}::{model}"
            if key in existing:
                continue
            normalized = scoring_module.score_sample(client, model, sample)
            row = {
                "group": entry["group"],
                "theme_id": entry["theme_id"],
                "theme": entry["theme"],
                "game_id": entry["game_id"],
                "segment_index": entry["segment_index"],
                "sample_id": sample.sample_id,
                "judge_model": model,
                "overall_score": normalized["overall_score"],
                "semantic_consistency": normalized["dimension_scores"]["semantic_consistency"],
                "subject_attribute_consistency": normalized["dimension_scores"]["subject_attribute_consistency"],
                "spatial_consistency": normalized["dimension_scores"]["spatial_consistency"],
                "style_lighting_consistency": normalized["dimension_scores"]["style_lighting_consistency"],
                "detail_integrity": normalized["dimension_scores"]["detail_integrity"],
                "confidence": normalized["confidence"],
                "reasons": normalized["reasons"],
                "failure_tags": normalized.get("failure_tags", []),
                "image_path": str(sample.image_path),
            }
            rows.append(row)
            write_jsonl(raw_path, rows)

    summary = summarize(rows, missing_rows)
    write_json(args.output_dir / "group_comparison_summary.json", summary)
    write_json(args.output_dir / "missing_samples.json", missing_rows)
    workbook = Workbook()
    workbook.remove(workbook.active)
    append_sheet(workbook, "group_comparison", summary)
    append_sheet(workbook, "per_sample_scores", rows)
    append_sheet(workbook, "missing_samples", missing_rows)
    workbook.save(args.output_dir / "paper_baseline_comparison.xlsx")
    print(args.output_dir / "paper_baseline_comparison.xlsx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

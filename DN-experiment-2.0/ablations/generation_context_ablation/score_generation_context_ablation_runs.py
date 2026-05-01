from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from openpyxl import Workbook  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Workbook = None  # type: ignore

THIS_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = THIS_DIR.parents[1]
REPO_ROOT = THIS_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")

from common import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_ROOT,
    append_sheet,
    as_text,
    flatten_task,
    load_config,
    load_json,
    make_key_value_rows,
    now_utc_iso,
    write_json,
    write_jsonl,
)


SCORE_SCRIPT_PATH = (
    EXPERIMENT_ROOT
    / "图片一致性_experiment"
    / "multiview_image_consistency"
    / "scripts"
    / "score_image_consistency_per_game.py"
)
AGG_SCRIPT_PATH = (
    EXPERIMENT_ROOT
    / "图片一致性_experiment"
    / "multiview_image_consistency"
    / "scripts"
    / "aggregate_multiview_results.py"
)
DEFAULT_SCORING_CONFIG_PATH = THIS_DIR / "configs" / "scoring_config.json"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def parse_models(models_csv: str) -> List[str]:
    return [part.strip() for part in (models_csv or "").split(",") if part.strip()]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def build_batch_name(custom_name: str) -> str:
    if custom_name.strip():
        return custom_name.strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"generation_context_ablation_score_batch_{timestamp}"


def build_group_summary(
    *,
    group_name: str,
    planned_eval_count: int,
    generation_rows: List[Dict[str, Any]],
    score_rows: List[Dict[str, Any]],
    scoring_module,
    aggregate_module,
    scoring_config: Dict[str, Any],
) -> Dict[str, Any]:
    eval_generation_rows = [
        row
        for row in generation_rows
        if row.get("task_type") == "eval" and row.get("group") == group_name
    ]
    successful_generation_rows = [row for row in eval_generation_rows if row.get("status") == "success"]
    duration_values = [
        float(row.get("duration_seconds"))
        for row in successful_generation_rows
        if row.get("duration_seconds") is not None
    ]
    average_duration = round(sum(duration_values) / len(duration_values), 4) if duration_values else None
    group_score_rows = [row for row in score_rows if row.get("group") == group_name]

    summary: Dict[str, Any] = {
        "group": group_name,
        "planned_eval_samples": planned_eval_count,
        "generated_eval_samples": len(successful_generation_rows),
        "generation_success_rate": round(len(successful_generation_rows) / planned_eval_count, 4) if planned_eval_count else 0.0,
        "coverage": 0.0,
        "valid_scored_samples": 0,
        "judge_row_count": len(group_score_rows),
        "overall_score_mean": None,
        "average_generation_seconds": average_duration,
    }

    dimensions = list(getattr(scoring_module, "DIMENSIONS", []))
    for dimension in dimensions:
        summary[f"{dimension}_mean"] = None

    if not group_score_rows:
        return summary

    normalized_group_score_rows: List[Dict[str, Any]] = []
    for row in group_score_rows:
        dimension_scores = row.get("dimension_scores")
        if not isinstance(dimension_scores, dict):
            dimension_scores = {
                dimension: row.get(dimension)
                for dimension in dimensions
                if row.get(dimension) is not None
            }
        normalized_row = dict(row)
        normalized_row["dimension_scores"] = dimension_scores
        normalized_group_score_rows.append(normalized_row)

    aggregate_payload = aggregate_module.aggregate(normalized_group_score_rows, scoring_config)
    dimension_summary = aggregate_payload.get("dimension_summary", {})
    unique_samples = {row["sample_id"] for row in group_score_rows if row.get("sample_id")}

    summary["valid_scored_samples"] = len(unique_samples)
    summary["coverage"] = round(len(unique_samples) / planned_eval_count, 4) if planned_eval_count else 0.0
    summary["overall_score_mean"] = aggregate_payload.get("overall_score_mean")
    for dimension in dimensions:
        summary[f"{dimension}_mean"] = (dimension_summary.get(dimension) or {}).get("mean")
    return summary


def build_group_comparison(group_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    comparable = [row for row in group_summaries if row.get("overall_score_mean") is not None]
    best_score = max(float(row["overall_score_mean"]) for row in comparable) if comparable else None

    baseline = next((row for row in group_summaries if row.get("group") == "prompt_plus_prev_image"), None)
    baseline_score = float(baseline["overall_score_mean"]) if baseline and baseline.get("overall_score_mean") is not None else None

    ranked = sorted(
        group_summaries,
        key=lambda row: float(row.get("overall_score_mean") or -999.0),
        reverse=True,
    )
    rank_map = {row["group"]: index + 1 for index, row in enumerate(ranked)}

    comparison_rows: List[Dict[str, Any]] = []
    for row in group_summaries:
        score = row.get("overall_score_mean")
        delta_best = None if score is None or best_score is None else round(float(score) - float(best_score), 4)
        delta_baseline = None if score is None or baseline_score is None else round(float(score) - float(baseline_score), 4)
        comparison_rows.append(
            {
                "group": row.get("group"),
                "overall_rank": rank_map.get(row.get("group"), ""),
                "overall_score_mean": score,
                "delta_vs_best": delta_best,
                "delta_vs_prompt_plus_prev_image": delta_baseline,
                "coverage": row.get("coverage"),
                "generation_success_rate": row.get("generation_success_rate"),
                "valid_scored_samples": row.get("valid_scored_samples"),
                "average_generation_seconds": row.get("average_generation_seconds"),
            }
        )
    return comparison_rows


def build_workbook(
    *,
    workbook_path: Path,
    dataset_tasks: List[Dict[str, Any]],
    generation_rows: List[Dict[str, Any]],
    score_rows: List[Dict[str, Any]],
    group_summaries: List[Dict[str, Any]],
    group_comparison: List[Dict[str, Any]],
    failure_rows: List[Dict[str, Any]],
    config_snapshot_rows: List[Dict[str, Any]],
) -> None:
    if Workbook is None:
        raise RuntimeError("openpyxl is not installed; cannot write xlsx. Re-run with --no-xlsx.")
    workbook = Workbook()
    workbook.remove(workbook.active)
    append_sheet(workbook, "dataset_manifest", dataset_tasks)
    append_sheet(workbook, "generation_runs", generation_rows)
    append_sheet(workbook, "per_sample_results", score_rows)
    append_sheet(workbook, "group_summary", group_summaries)
    append_sheet(workbook, "group_comparison", group_comparison)
    append_sheet(workbook, "failure_cases", failure_rows)
    append_sheet(workbook, "config_snapshot", config_snapshot_rows)
    workbook.save(workbook_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score previously generated generation-context ablation runs.")
    parser.add_argument(
        "--run-dirs",
        type=Path,
        nargs="+",
        required=True,
        help="One or more completed run directories produced by run_generation_context_ablation.py with --skip-scoring.",
    )
    parser.add_argument(
        "--judge-models",
        type=str,
        required=True,
        help="Comma-separated judge models, e.g. gpt-4o.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ablation config JSON path.",
    )
    parser.add_argument(
        "--scoring-config",
        type=Path,
        default=DEFAULT_SCORING_CONFIG_PATH,
        help="Scoring config JSON path used by the reused multiview aggregation logic.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for score-batch artifacts.",
    )
    parser.add_argument(
        "--batch-name",
        type=str,
        default="",
        help="Optional batch name for the merged scoring output.",
    )
    parser.add_argument(
        "--no-xlsx",
        action="store_true",
        help="Skip writing Excel workbook (avoids openpyxl dependency). JSON/JSONL artifacts are still produced.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    scoring_config = load_json(args.scoring_config)
    scoring_module = load_module("generation_context_ablation_score_only_module", SCORE_SCRIPT_PATH)
    aggregate_module = load_module("generation_context_ablation_aggregate_only_module", AGG_SCRIPT_PATH)

    judge_models = parse_models(args.judge_models)
    if not judge_models:
        raise SystemExit("No judge models were provided. Please pass --judge-models.")

    scoring_module.load_env()
    # Scoring logic (score_image_consistency_per_game.py) expects COHERENCE_* / VISION_REF_* env vars.
    # For convenience, allow "云雾" env vars and map them to the COHERENCE_* slots if present.
    if not (os.getenv("COHERENCE_API_KEY") or "").strip():
        yunwu_key = (os.getenv("YUNWU_API_KEY") or "").strip()
        if yunwu_key:
            os.environ["COHERENCE_API_KEY"] = yunwu_key
    if not (os.getenv("COHERENCE_BASE_URL") or "").strip():
        yunwu_base = (os.getenv("YUNWU_BASE_URL") or "").strip()
        if yunwu_base:
            os.environ["COHERENCE_BASE_URL"] = yunwu_base

    api_key = (os.getenv("COHERENCE_API_KEY") or "").strip() or (os.getenv("VISION_REF_API_KEY") or "").strip() or (os.getenv("Origin_Segment_Analyst_API_KEY") or "").strip()
    base_url = (os.getenv("COHERENCE_BASE_URL") or "").strip() or (os.getenv("VISION_REF_BASE_URL") or "").strip() or (os.getenv("Origin_Segment_Analyst_BASE_URL") or "").strip() or "https://api.openai.com/v1"
    if not api_key:
        raise SystemExit(
            "Missing judge API key. Set COHERENCE_API_KEY (preferred) or VISION_REF_API_KEY, "
            "or set YUNWU_API_KEY to use 云雾."
        )

    client = scoring_module.OpenAI(api_key=api_key, base_url=base_url)
    batch_name = build_batch_name(args.batch_name)
    batch_dir = args.output_root / "score_batches" / batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)

    combined_dataset_tasks: List[Dict[str, Any]] = []
    combined_generation_rows: List[Dict[str, Any]] = []
    combined_score_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    run_summaries: List[Dict[str, Any]] = []
    generation_index: Dict[Tuple[str, str, str, int], Dict[str, Any]] = {}

    for run_dir in args.run_dirs:
        resolved_run_dir = run_dir.resolve()
        run_name = resolved_run_dir.name
        dataset_manifest_path = resolved_run_dir / "dataset_manifest.json"
        generation_jsonl_path = resolved_run_dir / "generation_runs.jsonl"

        if not dataset_manifest_path.is_file():
            failure_rows.append(
                {
                    "stage": "setup",
                    "run_name": run_name,
                    "group": "",
                    "game_id": "",
                    "segment_index": "",
                    "reason": "dataset_manifest_missing",
                    "detail": f"Missing {dataset_manifest_path}",
                }
            )
            continue

        dataset_manifest = load_json(dataset_manifest_path)
        run_tasks = dataset_manifest.get("tasks", []) or []
        run_generation_rows = read_jsonl(generation_jsonl_path)
        run_summaries.append(
            {
                "run_name": run_name,
                "run_dir": str(resolved_run_dir),
                "dataset_name": as_text((dataset_manifest.get("summary") or {}).get("dataset_name")),
                "task_count": len(run_tasks),
                "generation_row_count": len(run_generation_rows),
            }
        )

        for task in run_tasks:
            task_row = flatten_task(task)
            task_row["run_name"] = run_name
            task_row["run_dir"] = str(resolved_run_dir)
            combined_dataset_tasks.append(task_row)

        for row in run_generation_rows:
            combined_row = dict(row)
            combined_row["run_name"] = run_name
            combined_row["run_dir"] = str(resolved_run_dir)
            combined_generation_rows.append(combined_row)

            try:
                segment_index = int(combined_row.get("segment_index"))
            except Exception:
                continue
            key = (
                run_name,
                as_text(combined_row.get("group")),
                as_text(combined_row.get("source_game_id")),
                segment_index,
            )
            generation_index[key] = combined_row

        for task in run_tasks:
            group_name = as_text(task.get("group"))
            source_game_id = as_text(task.get("game_id"))
            segment_index = int(task.get("segment_index"))
            current_key = (run_name, group_name, source_game_id, segment_index)
            previous_key = (run_name, group_name, source_game_id, segment_index - 1)
            current_generated = generation_index.get(current_key)
            previous_generated = generation_index.get(previous_key)

            if not current_generated or current_generated.get("status") != "success":
                failure_rows.append(
                    {
                        "stage": "scoring",
                        "run_name": run_name,
                        "group": group_name,
                        "game_id": source_game_id,
                        "segment_index": segment_index,
                        "reason": "missing_generated_image",
                        "detail": "Current generated image missing or generation did not succeed; sample skipped in scoring.",
                    }
                )
                continue

            current_image_path = Path(as_text(current_generated.get("generated_image_path")))
            if not current_image_path.is_file():
                failure_rows.append(
                    {
                        "stage": "scoring",
                        "run_name": run_name,
                        "group": group_name,
                        "game_id": source_game_id,
                        "segment_index": segment_index,
                        "reason": "generated_image_file_missing",
                        "detail": f"Missing file: {current_image_path}",
                    }
                )
                continue

            prev_image_path: Optional[Path] = None
            if previous_generated and previous_generated.get("status") == "success":
                candidate = Path(as_text(previous_generated.get("generated_image_path")))
                if candidate.is_file():
                    prev_image_path = candidate

            sample = scoring_module.Sample(
                game_id=source_game_id,
                theme_item_id=task.get("theme_id"),
                segment_index=segment_index,
                sample_id=f"{run_name}::{as_text(task.get('sample_id'))}",
                image_path=current_image_path,
                prompt_text=as_text(current_generated.get("used_prompt")).strip(),
                scene_text=as_text(task.get("source_scene")).strip(),
                prev_image_path=prev_image_path,
                prev_scene_text=as_text(task.get("source_previous_scene")).strip(),
            )

            for judge_model in judge_models:
                try:
                    normalized = scoring_module.score_sample(client, judge_model, sample)
                    combined_score_rows.append(
                        {
                            "run_name": run_name,
                            "run_dir": str(resolved_run_dir),
                            "group": group_name,
                            "theme_id": task.get("theme_id"),
                            "theme": task.get("theme"),
                            "source_game_id": source_game_id,
                            "sample_id": sample.sample_id,
                            "source_sample_id": as_text(task.get("sample_id")),
                            "segment_index": segment_index,
                            "judge_model": judge_model,
                            "overall_score": normalized["overall_score"],
                            "confidence": normalized["confidence"],
                            "dimension_scores": normalized["dimension_scores"],
                            "semantic_consistency": normalized["dimension_scores"]["semantic_consistency"],
                            "subject_attribute_consistency": normalized["dimension_scores"]["subject_attribute_consistency"],
                            "spatial_consistency": normalized["dimension_scores"]["spatial_consistency"],
                            "style_lighting_consistency": normalized["dimension_scores"]["style_lighting_consistency"],
                            "detail_integrity": normalized["dimension_scores"]["detail_integrity"],
                            "reasons": normalized["reasons"],
                            "failure_tags": normalized["failure_tags"],
                            "raw_response": normalized.get("raw_response", ""),
                        }
                    )
                except Exception as exc:
                    failure_rows.append(
                        {
                            "stage": "scoring",
                            "run_name": run_name,
                            "group": group_name,
                            "game_id": source_game_id,
                            "segment_index": segment_index,
                            "reason": "judge_failed",
                            "detail": f"{judge_model}: {exc}",
                        }
                    )

    planned_eval_by_group: Dict[str, int] = defaultdict(int)
    for task_row in combined_dataset_tasks:
        planned_eval_by_group[as_text(task_row.get("group"))] += 1

    group_summaries = [
        build_group_summary(
            group_name=group_name,
            planned_eval_count=planned_eval_by_group[group_name],
            generation_rows=combined_generation_rows,
            score_rows=combined_score_rows,
            scoring_module=scoring_module,
            aggregate_module=aggregate_module,
            scoring_config=scoring_config,
        )
        for group_name in config.get("groups", {}).keys()
    ]
    group_comparison = build_group_comparison(group_summaries)

    config_snapshot_rows = make_key_value_rows(
        {
            "batch_name": batch_name,
            "generated_at_utc": now_utc_iso(),
            "judge_models": judge_models,
            "scoring_config": scoring_config,
            "run_count": len(run_summaries),
            "runs": run_summaries,
            "groups": config.get("groups", {}),
            "runtime": config.get("runtime", {}),
            "selection": config.get("selection", {}),
        }
    )

    combined_manifest_payload = {
        "summary": {
            "batch_name": batch_name,
            "generated_at_utc": now_utc_iso(),
            "selected_tasks": len(combined_dataset_tasks),
            "selected_runs": len(run_summaries),
            "group_order": list(config.get("groups", {}).keys()),
        },
        "source_runs": run_summaries,
        "tasks": combined_dataset_tasks,
    }

    write_json(batch_dir / "dataset_manifest.json", combined_manifest_payload)
    write_jsonl(batch_dir / "generation_runs.jsonl", combined_generation_rows)
    write_jsonl(batch_dir / "per_sample_results.jsonl", combined_score_rows)
    write_json(batch_dir / "group_summary.json", group_summaries)
    write_json(batch_dir / "group_comparison.json", group_comparison)
    write_json(batch_dir / "failure_cases.json", failure_rows)
    write_json(batch_dir / "source_runs.json", run_summaries)

    for group_name in config.get("groups", {}).keys():
        group_generation_rows = [row for row in combined_generation_rows if row.get("group") == group_name]
        group_score_rows = [row for row in combined_score_rows if row.get("group") == group_name]
        group_summary = next((row for row in group_summaries if row.get("group") == group_name), None)
        group_dir = batch_dir / "groups" / group_name
        group_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(group_dir / "generation_results.jsonl", group_generation_rows)
        write_jsonl(group_dir / "score_results.jsonl", group_score_rows)
        write_json(group_dir / "summary.json", group_summary or {"group": group_name})

    workbook_path = batch_dir / "generation_context_ablation_results.xlsx"
    if not args.no_xlsx:
        build_workbook(
            workbook_path=workbook_path,
            dataset_tasks=combined_dataset_tasks,
            generation_rows=combined_generation_rows,
            score_rows=combined_score_rows,
            group_summaries=group_summaries,
            group_comparison=group_comparison,
            failure_rows=failure_rows,
            config_snapshot_rows=config_snapshot_rows,
        )

    print(f"score_batch_dir={batch_dir}")
    if not args.no_xlsx:
        print(f"workbook={workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from shared import (
    ABLATION_RESULTS_DIR,
    DEFAULT_JUDGE_GROUPS,
    LEGACY_RESULTS_DIR,
    THEMES_JSON,
    export_workbook_payload,
    find_default_legacy_scores_jsonl,
    flatten_group_models,
    get_dimensions,
    load_legacy_score_module,
    mean_or_none,
    population_stddev,
    read_json,
    read_jsonl,
    resolve_repo_path,
    round_or_none,
    utc_now,
    write_json,
)

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "evaluator_ablation_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run evaluator ablation on a fixed image-consistency dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Config JSON for paths and judge groups.")
    parser.add_argument("--dataset-json", type=Path, default=None, help="Dataset manifest JSON from build_evaluator_ablation_dataset.py.")
    parser.add_argument("--score-jsonl", type=Path, default=None, help="Optional existing raw judge scores JSONL to reuse first.")
    parser.add_argument("--output-dir", type=Path, default=ABLATION_RESULTS_DIR, help="Directory for ablation outputs.")
    parser.add_argument("--groups", type=str, default="", help="Comma-separated group_id/group_label filters.")
    parser.add_argument("--score-missing", action="store_true", help="If set, call legacy judge scoring for missing sample/model pairs.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call models; only reuse existing raw judge rows.")
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return read_json(path)


def resolve_dataset_json(config: Dict[str, Any], arg_path: Optional[Path]) -> Path:
    if arg_path is not None:
        return arg_path
    configured = resolve_repo_path((config.get("source_paths") or {}).get("latest_dataset_json"))
    if configured and configured.is_file():
        return configured
    fallback = ABLATION_RESULTS_DIR / "latest_dataset_manifest.json"
    return fallback


def resolve_score_jsonl(config: Dict[str, Any], arg_path: Optional[Path]) -> Optional[Path]:
    if arg_path is not None:
        return arg_path
    configured = resolve_repo_path((config.get("source_paths") or {}).get("legacy_scores_jsonl"))
    if configured and configured.is_file():
        return configured
    return find_default_legacy_scores_jsonl()


def normalize_groups(config: Dict[str, Any], group_filter: str) -> List[Dict[str, Any]]:
    groups = list(config.get("judge_groups") or DEFAULT_JUDGE_GROUPS)
    if not group_filter.strip():
        return groups
    wanted = {item.strip() for item in group_filter.split(",") if item.strip()}
    selected = [group for group in groups if group.get("group_id") in wanted or group.get("group_label") in wanted]
    if not selected:
        raise ValueError(f"No judge groups matched --groups={group_filter!r}")
    return selected


def load_dataset(path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    payload = read_json(path)
    dataset_manifest = list(payload.get("dataset_manifest") or [])
    selected = [row for row in dataset_manifest if row.get("selected") and row.get("is_available")]
    selection = dict(payload.get("selection") or {})
    return dataset_manifest, selected, selection


def normalize_raw_row(row: Dict[str, Any], sample_meta: Dict[str, Any], dimensions: List[str], source: str) -> Dict[str, Any]:
    dim_payload = row.get("dimension_scores") or {}
    if not dim_payload:
        dim_payload = {dim: row.get(dim) for dim in dimensions if row.get(dim) not in (None, "")}
    reasons = row.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [part.strip() for part in reasons.split("|") if part.strip()]
    failure_tags = row.get("failure_tags") or []
    if isinstance(failure_tags, str):
        failure_tags = [part.strip() for part in failure_tags.split(",") if part.strip()]
    normalized = {
        "sample_id": sample_meta["sample_id"],
        "theme_id": sample_meta["theme_id"],
        "theme": sample_meta["theme"],
        "game_id": sample_meta["game_id"],
        "segment_index": sample_meta["segment_index"],
        "image_path": sample_meta["image_path"],
        "judge_model": str(row.get("judge_model") or ""),
        "overall_score": float(row.get("overall_score")),
        "confidence": float(row.get("confidence", 0.0) or 0.0),
        "dimension_scores": {dim: float(dim_payload[dim]) for dim in dimensions if dim in dim_payload and dim_payload[dim] not in (None, "")},
        "reasons": reasons,
        "failure_tags": failure_tags,
        "runtime_seconds": row.get("runtime_seconds"),
        "source": source,
    }
    return normalized


def index_existing_scores(rows: Iterable[Dict[str, Any]], selected_by_id: Dict[str, Dict[str, Any]], dimensions: List[str]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row.get("sample_id") or "")
        judge_model = str(row.get("judge_model") or "")
        if not sample_id or not judge_model:
            continue
        if sample_id not in selected_by_id:
            continue
        overall = row.get("overall_score")
        if overall in (None, ""):
            continue
        try:
            normalized = normalize_raw_row(row, selected_by_id[sample_id], dimensions, source="existing_jsonl")
        except Exception:
            continue
        indexed[(sample_id, judge_model)] = normalized
    return indexed


def score_missing_rows(
    missing_pairs: List[Tuple[Dict[str, Any], str]],
    dimensions: List[str],
) -> List[Dict[str, Any]]:
    if not missing_pairs:
        return []
    legacy = load_legacy_score_module()
    legacy.load_env()
    api_key = legacy.env_str("COHERENCE_API_KEY") or legacy.env_str("VISION_REF_API_KEY") or legacy.env_str("Origin_Segment_Analyst_API_KEY")
    base_url = legacy.env_str("COHERENCE_BASE_URL") or legacy.env_str("VISION_REF_BASE_URL") or legacy.env_str("Origin_Segment_Analyst_BASE_URL") or "https://api.openai.com/v1"
    if not api_key:
        raise RuntimeError("Missing API key required for --score-missing.")
    client = legacy.OpenAI(api_key=api_key, base_url=base_url)
    scored_rows: List[Dict[str, Any]] = []
    for sample_meta, judge_model in missing_pairs:
        sample = legacy.Sample(
            game_id=str(sample_meta["game_id"]),
            theme_item_id=sample_meta["theme_id"],
            segment_index=int(sample_meta["segment_index"]),
            sample_id=str(sample_meta["sample_id"]),
            image_path=Path(sample_meta["image_path"]),
            prompt_text=str(sample_meta.get("prompt_text") or ""),
            scene_text=str(sample_meta.get("scene_text") or ""),
            prev_image_path=Path(sample_meta["prev_image_path"]) if sample_meta.get("prev_image_path") else None,
            prev_scene_text=str(sample_meta.get("prev_scene_text") or ""),
        )
        started = time.perf_counter()
        result = legacy.score_sample(client, judge_model, sample)
        elapsed = time.perf_counter() - started
        scored_rows.append(
            {
                "sample_id": sample_meta["sample_id"],
                "theme_id": sample_meta["theme_id"],
                "theme": sample_meta["theme"],
                "game_id": sample_meta["game_id"],
                "segment_index": sample_meta["segment_index"],
                "image_path": sample_meta["image_path"],
                "judge_model": judge_model,
                "overall_score": float(result["overall_score"]),
                "confidence": float(result["confidence"]),
                "dimension_scores": {dim: float(result["dimension_scores"][dim]) for dim in dimensions},
                "reasons": list(result.get("reasons") or []),
                "failure_tags": list(result.get("failure_tags") or []),
                "runtime_seconds": round(elapsed, 4),
                "source": "live_api",
            }
        )
    return scored_rows


def build_per_sample_results(
    dataset_selected: List[Dict[str, Any]],
    score_index: Dict[Tuple[str, str], Dict[str, Any]],
    groups: List[Dict[str, Any]],
    dimensions: List[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sample_meta in sorted(dataset_selected, key=lambda item: (int(item["theme_id"]), str(item["game_id"]), int(item["segment_index"]))):
        sample_id = str(sample_meta["sample_id"])
        for group in groups:
            judge_models = list(group["judge_models"])
            judge_rows = [score_index[(sample_id, model)] for model in judge_models if (sample_id, model) in score_index]
            overall_values = [row["overall_score"] for row in judge_rows]
            dimension_means = {
                dim: round_or_none(mean_or_none(row["dimension_scores"].get(dim) for row in judge_rows if dim in row["dimension_scores"]))
                for dim in dimensions
            }
            disagreement = round_or_none(population_stddev(overall_values)) if judge_rows else None
            per_dimension_spread = {
                dim: round_or_none(
                    (max(values) - min(values)) if len(values) >= 2 else (0.0 if len(values) == 1 else None)
                )
                for dim in dimensions
                for values in [[row["dimension_scores"].get(dim) for row in judge_rows if dim in row["dimension_scores"]]]
            }
            row = {
                "group_id": group["group_id"],
                "group_label": group["group_label"],
                "judge_models": ", ".join(judge_models),
                "required_judge_count": len(judge_models),
                "valid_judge_count": len(judge_rows),
                "judge_coverage": round(len(judge_rows) / len(judge_models), 4) if judge_models else 0.0,
                "theme_id": sample_meta["theme_id"],
                "theme": sample_meta["theme"],
                "game_id": sample_meta["game_id"],
                "segment_index": sample_meta["segment_index"],
                "sample_id": sample_id,
                "image_path": sample_meta["image_path"],
                "overall_score_mean": round_or_none(mean_or_none(overall_values)),
                "judge_disagreement": disagreement,
                "missing_judges": ", ".join([model for model in judge_models if (sample_id, model) not in score_index]),
                "judge_score_map_json": json.dumps({row["judge_model"]: row["overall_score"] for row in judge_rows}, ensure_ascii=False),
                "judge_confidence_map_json": json.dumps({row["judge_model"]: row["confidence"] for row in judge_rows}, ensure_ascii=False),
                "judge_reason_map_json": json.dumps({row["judge_model"]: row["reasons"] for row in judge_rows}, ensure_ascii=False),
                "runtime_seconds": round_or_none(sum(float(row.get("runtime_seconds") or 0.0) for row in judge_rows)) if judge_rows else None,
            }
            for dim in dimensions:
                row[f"{dim}_mean"] = dimension_means[dim]
                row[f"{dim}_spread"] = per_dimension_spread[dim]
            rows.append(row)
    return rows


def build_group_summary(per_sample_rows: List[Dict[str, Any]], groups: List[Dict[str, Any]], dimensions: List[str], total_selected_samples: int) -> List[Dict[str, Any]]:
    rows_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in per_sample_rows:
        rows_by_group[str(row["group_id"])].append(row)

    summaries: List[Dict[str, Any]] = []
    for group in groups:
        sample_rows = rows_by_group.get(group["group_id"], [])
        valid_rows = [row for row in sample_rows if row.get("valid_judge_count", 0) > 0 and row.get("overall_score_mean") is not None]
        full_rows = [row for row in sample_rows if row.get("valid_judge_count") == len(group["judge_models"])]
        summary = {
            "group_id": group["group_id"],
            "group_label": group["group_label"],
            "judge_models": ", ".join(group["judge_models"]),
            "judge_count": len(group["judge_models"]),
            "selected_sample_count": total_selected_samples,
            "valid_sample_count": len(valid_rows),
            "full_coverage_sample_count": len(full_rows),
            "coverage": round(len(full_rows) / total_selected_samples, 4) if total_selected_samples else 0.0,
            "partial_coverage_mean": round_or_none(mean_or_none(row["judge_coverage"] for row in sample_rows)),
            "overall_score_mean": round_or_none(mean_or_none(row["overall_score_mean"] for row in valid_rows)),
            "judge_disagreement_mean": round_or_none(mean_or_none(row["judge_disagreement"] for row in valid_rows if row["judge_disagreement"] is not None)),
            "runtime_seconds_total": round_or_none(sum(float(row.get("runtime_seconds") or 0.0) for row in valid_rows)) if valid_rows else None,
        }
        for dim in dimensions:
            summary[f"{dim}_mean"] = round_or_none(mean_or_none(row[f"{dim}_mean"] for row in valid_rows if row.get(f"{dim}_mean") is not None))
        summaries.append(summary)
    return summaries


def build_group_comparison(per_sample_rows: List[Dict[str, Any]], groups: List[Dict[str, Any]], dimensions: List[str]) -> List[Dict[str, Any]]:
    group_rows: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in per_sample_rows:
        if row.get("overall_score_mean") is None:
            continue
        group_rows[str(row["group_id"])][str(row["sample_id"])] = row

    comparisons: List[Dict[str, Any]] = []
    for index, left in enumerate(groups):
        left_rows = group_rows.get(left["group_id"], {})
        for right in groups[index + 1 :]:
            right_rows = group_rows.get(right["group_id"], {})
            common_sample_ids = sorted(set(left_rows) & set(right_rows))
            pair_rows_left = [left_rows[sample_id] for sample_id in common_sample_ids]
            pair_rows_right = [right_rows[sample_id] for sample_id in common_sample_ids]
            comparison = {
                "left_group_id": left["group_id"],
                "left_group_label": left["group_label"],
                "right_group_id": right["group_id"],
                "right_group_label": right["group_label"],
                "common_sample_count": len(common_sample_ids),
                "left_overall_score_mean": round_or_none(mean_or_none(row["overall_score_mean"] for row in pair_rows_left)),
                "right_overall_score_mean": round_or_none(mean_or_none(row["overall_score_mean"] for row in pair_rows_right)),
                "delta_overall_score_mean": round_or_none(
                    (mean_or_none(row["overall_score_mean"] for row in pair_rows_right) or 0.0)
                    - (mean_or_none(row["overall_score_mean"] for row in pair_rows_left) or 0.0)
                ) if common_sample_ids else None,
                "pairwise_mean_abs_diff": round_or_none(
                    mean_or_none(abs(right_rows[sample_id]["overall_score_mean"] - left_rows[sample_id]["overall_score_mean"]) for sample_id in common_sample_ids)
                ) if common_sample_ids else None,
                "delta_judge_disagreement_mean": round_or_none(
                    (mean_or_none(row["judge_disagreement"] for row in pair_rows_right if row.get("judge_disagreement") is not None) or 0.0)
                    - (mean_or_none(row["judge_disagreement"] for row in pair_rows_left if row.get("judge_disagreement") is not None) or 0.0)
                ) if common_sample_ids else None,
            }
            for dim in dimensions:
                left_mean = mean_or_none(row[f"{dim}_mean"] for row in pair_rows_left if row.get(f"{dim}_mean") is not None)
                right_mean = mean_or_none(row[f"{dim}_mean"] for row in pair_rows_right if row.get(f"{dim}_mean") is not None)
                comparison[f"left_{dim}_mean"] = round_or_none(left_mean)
                comparison[f"right_{dim}_mean"] = round_or_none(right_mean)
                comparison[f"delta_{dim}_mean"] = round_or_none((right_mean or 0.0) - (left_mean or 0.0)) if common_sample_ids else None
            comparisons.append(comparison)
    return comparisons


def build_disagreement_analysis(per_sample_rows: List[Dict[str, Any]], dimensions: List[str]) -> List[Dict[str, Any]]:
    analysis_rows: List[Dict[str, Any]] = []
    for row in per_sample_rows:
        if row.get("valid_judge_count", 0) < 2:
            continue
        spread_map = {dim: row.get(f"{dim}_spread") for dim in dimensions}
        ordered = sorted(((dim, spread or 0.0) for dim, spread in spread_map.items()), key=lambda item: item[1], reverse=True)
        top_dim, top_spread = ordered[0]
        analysis_rows.append(
            {
                "group_id": row["group_id"],
                "group_label": row["group_label"],
                "theme_id": row["theme_id"],
                "theme": row["theme"],
                "game_id": row["game_id"],
                "segment_index": row["segment_index"],
                "sample_id": row["sample_id"],
                "overall_score_mean": row["overall_score_mean"],
                "judge_disagreement": row["judge_disagreement"],
                "top_disagreement_dimension": top_dim,
                "top_dimension_spread": top_spread,
                "judge_models": row["judge_models"],
                "judge_score_map_json": row["judge_score_map_json"],
                "judge_reason_map_json": row["judge_reason_map_json"],
            }
        )
    analysis_rows.sort(key=lambda item: ((item.get("judge_disagreement") or 0.0), (item.get("top_dimension_spread") or 0.0)), reverse=True)
    return analysis_rows


def build_run_metadata(
    config_path: Path,
    dataset_json: Path,
    score_jsonl: Optional[Path],
    groups: List[Dict[str, Any]],
    selection: Dict[str, Any],
    missing_pairs: List[Tuple[Dict[str, Any], str]],
    live_rows: List[Dict[str, Any]],
    wallclock_seconds: float,
    score_missing_enabled: bool,
) -> List[Dict[str, Any]]:
    return [
        {"key": "generated_at_utc", "value": utc_now().isoformat()},
        {"key": "config", "value": str(config_path)},
        {"key": "dataset_json", "value": str(dataset_json)},
        {"key": "score_jsonl", "value": str(score_jsonl) if score_jsonl else ""},
        {"key": "selected_sample_count", "value": selection.get("selected_sample_count")},
        {"key": "selected_theme_count", "value": selection.get("selected_theme_count")},
        {"key": "judge_groups", "value": " | ".join(group["group_label"] for group in groups)},
        {"key": "required_judge_models", "value": ", ".join(flatten_group_models(groups))},
        {"key": "missing_sample_model_pairs_before_scoring", "value": len(missing_pairs)},
        {"key": "live_api_rows_added", "value": len(live_rows)},
        {"key": "wallclock_seconds", "value": round(wallclock_seconds, 4)},
        {"key": "score_missing_enabled", "value": score_missing_enabled},
    ]


def main() -> int:
    started = time.perf_counter()
    args = parse_args()
    config = load_config(args.config)

    # Map 云雾 env vars to the legacy scorer env slots when present.
    if not (os.getenv("COHERENCE_API_KEY") or "").strip():
        yunwu_key = (os.getenv("YUNWU_API_KEY") or "").strip()
        if yunwu_key:
            os.environ["COHERENCE_API_KEY"] = yunwu_key
    if not (os.getenv("COHERENCE_BASE_URL") or "").strip():
        yunwu_base = (os.getenv("YUNWU_BASE_URL") or "").strip()
        if yunwu_base:
            os.environ["COHERENCE_BASE_URL"] = yunwu_base

    dataset_json = resolve_dataset_json(config, args.dataset_json)
    if not dataset_json.is_file():
        raise FileNotFoundError(f"Dataset manifest JSON not found: {dataset_json}")
    score_jsonl = resolve_score_jsonl(config, args.score_jsonl)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    groups = normalize_groups(config, args.groups)
    dimensions = get_dimensions()
    dataset_manifest, dataset_selected, selection = load_dataset(dataset_json)
    selected_by_id = {str(row["sample_id"]): row for row in dataset_selected}

    existing_rows = read_jsonl(score_jsonl) if score_jsonl and score_jsonl.is_file() else []
    score_index = index_existing_scores(existing_rows, selected_by_id, dimensions)

    missing_pairs: List[Tuple[Dict[str, Any], str]] = []
    for sample_meta in dataset_selected:
        for judge_model in flatten_group_models(groups):
            key = (str(sample_meta["sample_id"]), judge_model)
            if key not in score_index:
                missing_pairs.append((sample_meta, judge_model))

    live_rows: List[Dict[str, Any]] = []
    if missing_pairs and args.score_missing and not args.dry_run:
        live_rows = score_missing_rows(missing_pairs, dimensions)
        for row in live_rows:
            score_index[(str(row["sample_id"]), str(row["judge_model"]))] = row

    raw_judge_rows = sorted(score_index.values(), key=lambda item: (int(item["theme_id"]), str(item["game_id"]), int(item["segment_index"]), str(item["judge_model"])))
    per_sample_rows = build_per_sample_results(dataset_selected, score_index, groups, dimensions)
    per_group_summary = build_group_summary(per_sample_rows, groups, dimensions, len(dataset_selected))
    group_comparison = build_group_comparison(per_sample_rows, groups, dimensions)
    disagreement_analysis = build_disagreement_analysis(per_sample_rows, dimensions)
    run_metadata = build_run_metadata(
        args.config,
        dataset_json,
        score_jsonl,
        groups,
        selection,
        missing_pairs,
        live_rows,
        time.perf_counter() - started,
        args.score_missing,
    )

    summary_json = output_dir / "latest_evaluator_ablation_summary.json"
    workbook_path = output_dir / "latest_evaluator_ablation.xlsx"
    summary_payload = {
        "generated_at_utc": utc_now().isoformat(),
        "dataset_json": str(dataset_json),
        "score_jsonl": str(score_jsonl) if score_jsonl else None,
        "groups": groups,
        "selection": selection,
        "missing_pairs_before_scoring": len(missing_pairs),
        "live_api_rows_added": len(live_rows),
        "run_metadata": run_metadata,
        "per_group_summary": per_group_summary,
        "group_comparison": group_comparison,
        "disagreement_analysis_top10": disagreement_analysis[:10],
    }
    write_json(summary_json, summary_payload)
    workbook_payload_obj = {
        "mode": "analysis",
        "dataset_manifest": dataset_manifest,
        "run_metadata": run_metadata,
        "per_sample_results": per_sample_rows,
        "per_group_summary": per_group_summary,
        "group_comparison": group_comparison,
        "disagreement_analysis": disagreement_analysis,
    }
    export_workbook_payload("analysis", workbook_payload_obj, workbook_path)

    print(
        json.dumps(
            {
                "dataset_json": str(dataset_json),
                "score_jsonl": str(score_jsonl) if score_jsonl else None,
                "missing_pairs_before_scoring": len(missing_pairs),
                "live_api_rows_added": len(live_rows),
                "workbook_path": str(workbook_path),
                "summary_json": str(summary_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

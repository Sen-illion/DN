from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from shared import (
    DATASETS_DIR,
    DEFAULT_CONFIG_PATH,
    LEGACY_AGGREGATE_SCRIPT,
    LEGACY_SCORE_SCRIPT,
    RESULTS_DIR,
    copy_latest,
    coverage_ratio,
    flatten_dict,
    get_dimensions,
    get_group_specs,
    latest_dataset_manifest_path,
    load_config,
    mean_or_none,
    population_stddev,
    read_json,
    read_jsonl,
    round_or_none,
    run_python_script,
    safe_text,
    slugify,
    utc_now,
    utc_timestamp,
    write_json,
    write_jsonl,
    write_workbook,
)

from src.image.api_providers import (
    generate_main_character_image,
    generate_scene_image,
    resolve_protagonist_reference_views,
)

_EXPERIMENT_SAVE = REPO_ROOT / "DN-experiment" / "experiment_save.py"
_EXPORT_IMAGE_PATHS = REPO_ROOT / "DN-experiment-2.0" / "export_image_paths_manifest.py"

_save_spec = importlib.util.spec_from_file_location("dn_experiment_save", _EXPERIMENT_SAVE)
if _save_spec is None or _save_spec.loader is None:
    raise RuntimeError(f"Unable to load {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_save_spec)
_save_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder
experiment_dir_name = _save_mod.experiment_dir_name

_export_spec = importlib.util.spec_from_file_location("export_image_paths_manifest", _EXPORT_IMAGE_PATHS)
if _export_spec is None or _export_spec.loader is None:
    raise RuntimeError(f"Unable to load {_EXPORT_IMAGE_PATHS}")
_export_mod = importlib.util.module_from_spec(_export_spec)
_export_spec.loader.exec_module(_export_mod)
build_manifest_for_folder = _export_mod.build_manifest_for_folder

IMAGE_CACHE_ROOT = REPO_ROOT / "image_cache"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run protagonist reference count ablation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Config JSON path.")
    parser.add_argument("--dataset-manifest", type=Path, default=None, help="dataset_manifest.jsonl path.")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR, help="Run output root.")
    parser.add_argument("--run-name", type=str, default="", help="Optional stable run directory name.")
    parser.add_argument("--groups", type=str, default="", help="Comma-separated group ids to run.")
    parser.add_argument("--judge-models", type=str, default="", help="Override comma-separated judge models.")
    parser.add_argument("--skip-scoring", action="store_true", help="Skip legacy scoring and aggregation.")
    parser.add_argument("--no-xlsx", action="store_true", help="Skip writing Excel workbook (avoids openpyxl dependency).")
    parser.add_argument("--max-samples", type=int, default=0, help="Optional cap on manifest rows per group.")
    parser.add_argument("--smoke-segments", type=int, default=0, help="Optional cap on segments per game for smoke runs.")
    parser.add_argument("--view-wait-seconds", type=int, default=240, help="Wait timeout for protagonist views.")
    return parser.parse_args()


def resolve_dataset_manifest(path: Optional[Path]) -> Path:
    if path is not None:
        return path
    latest = latest_dataset_manifest_path()
    if latest is None:
        raise FileNotFoundError("No dataset manifest provided and no latest dataset manifest found.")
    return latest


def group_rows_by_game(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["base_game_id"])].append(row)
    for game_id in grouped:
        grouped[game_id].sort(key=lambda item: int(item.get("segment_index") or 0))
    return dict(grouped)


def choose_groups(all_groups: List[Dict[str, Any]], selected_csv: str) -> List[Dict[str, Any]]:
    if not selected_csv.strip():
        return list(all_groups)
    selected_ids = {token.strip() for token in selected_csv.split(",") if token.strip()}
    return [group for group in all_groups if group["group_id"] in selected_ids]


def wait_for_protagonist_views(game_id: str, expected_count: int, timeout_seconds: int) -> Dict[str, Any]:
    start = time.perf_counter()
    while True:
        resolved = resolve_protagonist_reference_views(game_id)
        available_paths = [path for path in (resolved.get("front"), resolved.get("side"), resolved.get("back")) if path]
        if len(available_paths) >= expected_count:
            return {
                "ready": True,
                "wait_seconds": round(time.perf_counter() - start, 4),
                "available_paths": available_paths,
                "resolved_views": resolved,
            }
        if time.perf_counter() - start >= timeout_seconds:
            return {
                "ready": False,
                "wait_seconds": round(time.perf_counter() - start, 4),
                "available_paths": available_paths,
                "resolved_views": resolved,
            }
        time.sleep(2)


def build_run_game_id(base_game_id: str, group_id: str) -> str:
    return f"{base_game_id}_{slugify(group_id)}"


def prepare_shared_protagonist_references(
    dataset_rows: List[Dict[str, Any]],
    group_specs: List[Dict[str, Any]],
    view_wait_seconds: int,
) -> Dict[str, Dict[str, Any]]:
    group_expected = {
        str(group["group_id"]): int(group.get("expected_protagonist_ref_count") or 0)
        for group in group_specs
    }
    rows_by_game: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    required_counts: Dict[str, int] = defaultdict(int)
    for row in dataset_rows:
        base_game_id = str(row.get("base_game_id") or "").strip()
        if not base_game_id:
            continue
        rows_by_game[base_game_id].append(row)
        group_id = str(row.get("protagonist_ref_group") or "").strip()
        required_counts[base_game_id] = max(required_counts[base_game_id], group_expected.get(group_id, 0))

    prepared: Dict[str, Dict[str, Any]] = {}
    for base_game_id, rows in sorted(rows_by_game.items()):
        required_count = int(required_counts.get(base_game_id) or 0)
        info = {"ready": True, "wait_seconds": 0.0, "available_paths": [], "resolved_views": {}}
        if required_count <= 0:
            prepared[base_game_id] = info
            continue

        build_context = read_json(Path(rows[0]["build_context_path"]))
        protagonist_attr = build_context.get("protagonist_attr") if isinstance(build_context.get("protagonist_attr"), dict) else {}
        image_style = build_context.get("image_style") if isinstance(build_context.get("image_style"), dict) else {}
        first_state = read_json(Path(rows[0]["state_snapshot_path"]))
        first_state["game_id"] = base_game_id
        if image_style:
            first_state["image_style"] = image_style
        generate_main_character_image(
            protagonist_attr=protagonist_attr,
            global_state=first_state,
            image_style=image_style,
            game_id=base_game_id,
        )
        info = wait_for_protagonist_views(base_game_id, required_count, view_wait_seconds)
        prepared[base_game_id] = info
    return prepared


def snapshot_image_cache() -> Dict[str, Tuple[int, int]]:
    snapshot: Dict[str, Tuple[int, int]] = {}
    if not IMAGE_CACHE_ROOT.is_dir():
        return snapshot
    for path in IMAGE_CACHE_ROOT.glob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path.name] = (int(stat.st_mtime_ns), int(stat.st_size))
    return snapshot


def resolve_local_cache_url(url: str) -> Optional[Path]:
    text = str(url or "").strip().replace("\\", "/")
    if not text:
        return None
    if text.startswith("/image_cache/"):
        candidate = IMAGE_CACHE_ROOT / Path(text).name
        return candidate if candidate.is_file() else None
    if text.startswith("image_cache/"):
        candidate = IMAGE_CACHE_ROOT / Path(text).name
        return candidate if candidate.is_file() else None
    return None


def detect_new_image_cache_files(before: Dict[str, Tuple[int, int]]) -> List[Path]:
    candidates: List[Tuple[int, Path]] = []
    after = snapshot_image_cache()
    for name, state in after.items():
        if before.get(name) == state:
            continue
        path = IMAGE_CACHE_ROOT / name
        if not path.is_file():
            continue
        try:
            mtime_ns = int(path.stat().st_mtime_ns)
        except OSError:
            continue
        candidates.append((mtime_ns, path))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in candidates]


def repair_missing_local_cache_url(
    image_data: Optional[Dict[str, Any]],
    cache_before: Dict[str, Tuple[int, int]],
) -> Tuple[Optional[Dict[str, Any]], str]:
    if not isinstance(image_data, dict):
        return image_data, ""

    url = str(image_data.get("url") or "").strip()
    if not url:
        return image_data, ""
    if not (url.startswith("/image_cache/") or url.startswith("image_cache/")):
        return image_data, ""
    if resolve_local_cache_url(url) is not None:
        return image_data, ""

    new_cache_files = detect_new_image_cache_files(cache_before)
    if not new_cache_files:
        return image_data, ""

    repaired = dict(image_data)
    repaired_url = f"/image_cache/{new_cache_files[0].name}"
    repaired["url"] = repaired_url
    note = (
        "returned image_cache path was missing locally; "
        f"runner remapped to newest cache file {new_cache_files[0].name}"
    )
    return repaired, note


def export_group_manifests(group_root: Path) -> List[Path]:
    manifest_paths: List[Path] = []
    for game_folder in sorted(group_root.glob("theme_*")):
        if not game_folder.is_dir():
            continue
        manifest = build_manifest_for_folder(REPO_ROOT, game_folder)
        if not manifest:
            continue
        manifest_path = game_folder / f"{manifest['game_id']}_image_paths.json"
        write_json(manifest_path, manifest)
        manifest_paths.append(manifest_path)
    return manifest_paths


def score_group(group_root: Path, output_dir: Path, judge_models: str) -> None:
    args = [
        "--experiment-root",
        str(group_root),
        "--output-dir",
        str(output_dir),
        "--models",
        judge_models,
    ]
    run_python_script(LEGACY_SCORE_SCRIPT, args, cwd=REPO_ROOT)


def aggregate_group(score_dir: Path, aggregate_config_path: Path) -> None:
    input_jsonl = score_dir / "latest_per_game_image_scores.jsonl"
    if not input_jsonl.is_file():
        return
    args = [
        "--input-jsonl",
        str(input_jsonl),
        "--config",
        str(aggregate_config_path),
        "--output-dir",
        str(score_dir),
    ]
    run_python_script(LEGACY_AGGREGATE_SCRIPT, args, cwd=REPO_ROOT)


def aggregate_per_sample(score_rows: List[Dict[str, Any]], generation_lookup: Dict[str, Dict[str, Any]], dimensions: List[str]) -> List[Dict[str, Any]]:
    bucket: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        sample_id = str(row.get("sample_id") or "").strip()
        if sample_id:
            bucket[sample_id].append(row)

    results: List[Dict[str, Any]] = []
    for sample_id, rows in sorted(bucket.items()):
        base = dict(generation_lookup.get(sample_id, {}))
        models = sorted({str(row.get("judge_model") or "") for row in rows if row.get("judge_model")})
        result = {
            **base,
            "sample_id": sample_id,
            "judge_model_count": len(models),
            "judge_models": ",".join(models),
            "overall_score_mean": round_or_none(mean_or_none(row.get("overall_score") for row in rows)),
            "confidence_mean": round_or_none(mean_or_none(row.get("confidence") for row in rows)),
            "judge_overall_stddev": round_or_none(population_stddev(row.get("overall_score") for row in rows)),
            "failure_tags": sorted({tag for row in rows for tag in (row.get("failure_tags") or []) if tag}),
            "reason_preview": " | ".join(
                dict.fromkeys(
                    safe_text(reason, 140)
                    for row in rows
                    for reason in (row.get("reasons") or [])
                    if reason
                )
            )[:500],
        }
        for dimension in dimensions:
            result[f"{dimension}_mean"] = round_or_none(
                mean_or_none(row.get(dimension) for row in rows)
            )
        result["reference_identity_fidelity_mean"] = result.get("subject_attribute_consistency_mean")
        result["view_match_accuracy_mean"] = result.get("spatial_consistency_mean")
        results.append(result)
    return results


def build_group_summary(
    group_rows: List[Dict[str, Any]],
    generation_rows: List[Dict[str, Any]],
    per_sample_rows: List[Dict[str, Any]],
    dimensions: List[str],
) -> List[Dict[str, Any]]:
    generation_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    per_sample_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    dataset_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in group_rows:
        dataset_by_group[str(row["protagonist_ref_group"])].append(row)
    for row in generation_rows:
        generation_by_group[str(row["protagonist_ref_group"])].append(row)
    for row in per_sample_rows:
        per_sample_by_group[str(row["protagonist_ref_group"])].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group_id in sorted(dataset_by_group):
        planned = dataset_by_group[group_id]
        generated = generation_by_group.get(group_id, [])
        scored = per_sample_by_group.get(group_id, [])
        success_rows = [row for row in generated if row.get("generation_success")]
        summary = {
            "protagonist_ref_group": group_id,
            "dataset_variant": next((row.get("dataset_variant") for row in planned if row.get("dataset_variant")), "general"),
            "planned_samples": len(planned),
            "generated_samples": len(success_rows),
            "valid_samples": len(scored),
            "coverage": round_or_none(coverage_ratio(len(scored), len(planned))),
            "success_generation_rate": round_or_none(coverage_ratio(len(success_rows), len(planned))),
            "avg_actual_protagonist_ref_count": round_or_none(mean_or_none(row.get("actual_protagonist_ref_count") for row in success_rows)),
            "avg_generation_duration_seconds": round_or_none(mean_or_none(row.get("duration_seconds") for row in success_rows)),
            "overall_score_mean": round_or_none(mean_or_none(row.get("overall_score_mean") for row in scored)),
            "reference_identity_fidelity_mean": round_or_none(mean_or_none(row.get("reference_identity_fidelity_mean") for row in scored)),
            "reference_identity_fidelity_stddev": round_or_none(population_stddev(row.get("reference_identity_fidelity_mean") for row in scored)),
            "view_match_accuracy_mean": round_or_none(mean_or_none(row.get("view_match_accuracy_mean") for row in scored)),
        }
        for dimension in dimensions:
            summary[f"{dimension}_mean"] = round_or_none(mean_or_none(row.get(f"{dimension}_mean") for row in scored))
        summary_rows.append(summary)
    return summary_rows


def build_group_comparison(summary_rows: List[Dict[str, Any]], dimensions: List[str]) -> List[Dict[str, Any]]:
    baseline = None
    for row in summary_rows:
        if row.get("protagonist_ref_group") == "protagonist_ref_0":
            baseline = row
            break
    comparison_rows: List[Dict[str, Any]] = []
    for row in summary_rows:
        comparison = dict(row)
        if baseline is not None:
            comparison["overall_delta_vs_protagonist_ref_0"] = round_or_none(
                (row.get("overall_score_mean") or 0.0) - (baseline.get("overall_score_mean") or 0.0)
            )
            comparison["coverage_delta_vs_protagonist_ref_0"] = round_or_none(
                (row.get("coverage") or 0.0) - (baseline.get("coverage") or 0.0)
            )
            comparison["success_rate_delta_vs_protagonist_ref_0"] = round_or_none(
                (row.get("success_generation_rate") or 0.0) - (baseline.get("success_generation_rate") or 0.0)
            )
            for dimension in dimensions:
                comparison[f"{dimension}_delta_vs_protagonist_ref_0"] = round_or_none(
                    (row.get(f"{dimension}_mean") or 0.0) - (baseline.get(f"{dimension}_mean") or 0.0)
                )
        comparison_rows.append(comparison)
    comparison_rows.sort(key=lambda item: (-(item.get("overall_score_mean") or 0.0), item.get("protagonist_ref_group") or ""))
    for index, row in enumerate(comparison_rows, start=1):
        row["rank_by_overall_score"] = index
    return comparison_rows


def build_subset_summary(
    per_sample_rows: List[Dict[str, Any]],
    dimensions: List[str],
    subset_field: str,
) -> List[Dict[str, Any]]:
    bucket: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in per_sample_rows:
        group_id = str(row.get("protagonist_ref_group") or "")
        subset_value = str(row.get(subset_field) or "unspecified")
        if group_id:
            bucket[(subset_value, group_id)].append(row)

    rows: List[Dict[str, Any]] = []
    for (subset_value, group_id), items in sorted(bucket.items()):
        summary = {
            subset_field: subset_value,
            "protagonist_ref_group": group_id,
            "valid_samples": len(items),
            "overall_score_mean": round_or_none(mean_or_none(row.get("overall_score_mean") for row in items)),
            "reference_identity_fidelity_mean": round_or_none(mean_or_none(row.get("reference_identity_fidelity_mean") for row in items)),
            "reference_identity_fidelity_stddev": round_or_none(population_stddev(row.get("reference_identity_fidelity_mean") for row in items)),
            "view_match_accuracy_mean": round_or_none(mean_or_none(row.get("view_match_accuracy_mean") for row in items)),
        }
        for dimension in dimensions:
            summary[f"{dimension}_mean"] = round_or_none(mean_or_none(row.get(f"{dimension}_mean") for row in items))
        rows.append(summary)
    return rows


def build_failure_cases(
    generation_rows: List[Dict[str, Any]],
    per_sample_rows: List[Dict[str, Any]],
    dimensions: List[str],
) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    scored_ids = {str(row.get("sample_id") or "") for row in per_sample_rows}
    for row in generation_rows:
        if not row.get("generation_success"):
            failures.append(
                {
                    "failure_stage": "generation",
                    "protagonist_ref_group": row.get("protagonist_ref_group"),
                    "sample_id": row.get("sample_id"),
                    "theme_id": row.get("theme_id"),
                    "base_game_id": row.get("base_game_id"),
                    "run_game_id": row.get("run_game_id"),
                    "segment_index": row.get("segment_index"),
                    "details": row.get("error_message") or "scene generation failed",
                }
            )
        elif str(row.get("sample_id") or "") not in scored_ids:
            failures.append(
                {
                    "failure_stage": "scoring_missing",
                    "protagonist_ref_group": row.get("protagonist_ref_group"),
                    "sample_id": row.get("sample_id"),
                    "theme_id": row.get("theme_id"),
                    "base_game_id": row.get("base_game_id"),
                    "run_game_id": row.get("run_game_id"),
                    "segment_index": row.get("segment_index"),
                    "details": "generation succeeded but legacy scorer produced no row",
                }
            )
    for row in per_sample_rows:
        overall = row.get("overall_score_mean")
        if overall is not None and float(overall) < 3.0:
            failures.append(
                {
                    "failure_stage": "low_score",
                    "protagonist_ref_group": row.get("protagonist_ref_group"),
                    "sample_id": row.get("sample_id"),
                    "theme_id": row.get("theme_id"),
                    "base_game_id": row.get("base_game_id"),
                    "run_game_id": row.get("run_game_id"),
                    "segment_index": row.get("segment_index"),
                    "details": row.get("reason_preview") or "overall score below 3.0",
                }
            )
    return failures


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    dimensions = get_dimensions()

    # Map 云雾 env vars to the legacy scorer env slots when present.
    if not (os.getenv("COHERENCE_API_KEY") or "").strip():
        yunwu_key = (os.getenv("YUNWU_API_KEY") or "").strip()
        if yunwu_key:
            os.environ["COHERENCE_API_KEY"] = yunwu_key
    if not (os.getenv("COHERENCE_BASE_URL") or "").strip():
        yunwu_base = (os.getenv("YUNWU_BASE_URL") or "").strip()
        if yunwu_base:
            os.environ["COHERENCE_BASE_URL"] = yunwu_base

    group_specs = choose_groups(get_group_specs(config), args.groups)
    dataset_manifest_path = resolve_dataset_manifest(args.dataset_manifest)
    dataset_rows = read_jsonl(dataset_manifest_path)
    if not dataset_rows:
        raise SystemExit(f"Dataset manifest is empty: {dataset_manifest_path}")
    dataset_variant = str(dataset_rows[0].get("dataset_variant") or "general")

    if args.max_samples > 0:
        trimmed_by_group: Dict[str, int] = defaultdict(int)
        trimmed_rows: List[Dict[str, Any]] = []
        for row in dataset_rows:
            group_id = str(row.get("protagonist_ref_group") or "")
            if trimmed_by_group[group_id] >= args.max_samples:
                continue
            trimmed_rows.append(row)
            trimmed_by_group[group_id] += 1
        dataset_rows = trimmed_rows

    if args.smoke_segments > 0:
        per_game_segment_counter: Dict[Tuple[str, str], int] = defaultdict(int)
        trimmed_rows = []
        for row in dataset_rows:
            key = (str(row.get("protagonist_ref_group") or ""), str(row.get("base_game_id") or ""))
            if per_game_segment_counter[key] >= args.smoke_segments:
                continue
            trimmed_rows.append(row)
            per_game_segment_counter[key] += 1
        dataset_rows = trimmed_rows

    variant_output_dir = args.output_dir if dataset_variant == "general" else args.output_dir / dataset_variant
    run_id_prefix = "protagonist_ref_run" if dataset_variant == "general" else f"protagonist_ref_{dataset_variant}_run"
    run_id = args.run_name.strip() or f"{run_id_prefix}_{utc_timestamp()}"
    run_dir = variant_output_dir / run_id
    generated_root = run_dir / "generated"
    scoring_root = run_dir / "scoring"
    analysis_root = run_dir / "analysis"
    generated_root.mkdir(parents=True, exist_ok=True)
    scoring_root.mkdir(parents=True, exist_ok=True)
    analysis_root.mkdir(parents=True, exist_ok=True)

    scoring_cfg = config.get("scoring") or {}
    judge_models = args.judge_models.strip() or str(scoring_cfg.get("judge_models_csv") or ",".join(scoring_cfg.get("judge_models") or []))

    generation_rows: List[Dict[str, Any]] = []
    protagonist_usage_rows: List[Dict[str, Any]] = []
    updated_dataset_rows: List[Dict[str, Any]] = []
    score_rows_all: List[Dict[str, Any]] = []
    shared_protagonist_refs = prepare_shared_protagonist_references(
        dataset_rows,
        group_specs,
        args.view_wait_seconds,
    )

    for group in group_specs:
        group_id = group["group_id"]
        expected_count = int(group["expected_protagonist_ref_count"])
        group_output_root = generated_root / group_id
        group_output_root.mkdir(parents=True, exist_ok=True)
        group_rows = [row for row in dataset_rows if str(row.get("protagonist_ref_group") or "") == group_id]
        games = group_rows_by_game(group_rows)

        for base_game_id, rows in games.items():
            build_context_path = Path(rows[0]["build_context_path"])
            build_context = read_json(build_context_path)
            image_style = build_context.get("image_style") if isinstance(build_context.get("image_style"), dict) else {}
            theme_id = int(build_context.get("theme_id") or rows[0]["theme_id"])
            run_game_id = build_run_game_id(base_game_id, group_id)
            front_wait = dict(shared_protagonist_refs.get(base_game_id) or {"ready": True, "wait_seconds": 0.0, "available_paths": [], "resolved_views": {}})

            previous_scene_image: Dict[str, Any] = {}
            previous_scene_text = ""
            for row in rows:
                scene_payload = read_json(Path(row["scene_json_path"]))
                state_snapshot = read_json(Path(row["state_snapshot_path"]))
                state_snapshot["game_id"] = run_game_id
                state_snapshot["tone"] = str(build_context.get("tone_key") or state_snapshot.get("tone") or "normal_ending")
                if image_style:
                    state_snapshot["image_style"] = image_style
                state_snapshot["_experiment_protagonist_ref_group"] = group_id
                state_snapshot["_experiment_expected_protagonist_ref_count"] = expected_count
                state_snapshot["_experiment_protagonist_ref_count_limit"] = expected_count
                state_snapshot["_experiment_protagonist_reference_game_id"] = base_game_id
                if expected_count == 0:
                    state_snapshot["_skip_protagonist_reference"] = True
                else:
                    state_snapshot.pop("_skip_protagonist_reference", None)
                if previous_scene_image.get("url"):
                    state_snapshot["_visual_context"] = {
                        "sceneId": f"{run_game_id}_seg{int(row['segment_index']) - 1}",
                        "previousSceneImage": previous_scene_image,
                        "previousSceneText": previous_scene_text,
                    }
                else:
                    state_snapshot.pop("_visual_context", None)

                scene_text = str(scene_payload.get("scene") or "")
                segment_index = int(row["segment_index"])
                sample_id = f"{run_game_id}_seg_{segment_index:03d}"
                cache_suffix = f"{run_id}_{group_id}_{sample_id}"
                start_ts = utc_now().isoformat()
                started = time.perf_counter()
                image_data = None
                error_message = ""
                cache_before = snapshot_image_cache()
                try:
                    image_data = generate_scene_image(
                        scene_text,
                        state_snapshot,
                        "default",
                        use_cache=True,
                        cache_key_suffix=cache_suffix,
                        skip_cache_lookup=True,
                    )
                except Exception as exc:
                    error_message = str(exc)
                duration_seconds = round(time.perf_counter() - started, 4)
                end_ts = utc_now().isoformat()
                image_data, cache_repair_note = repair_missing_local_cache_url(image_data, cache_before)
                if cache_repair_note:
                    error_message = f"{error_message} | {cache_repair_note}".strip(" |")

                generation_success = bool(isinstance(image_data, dict) and image_data.get("url"))
                saved_json_path = ""
                saved_image_path = ""
                usage = image_data.get("protagonist_reference_usage") if generation_success else {}
                prompt_json = state_snapshot.get("_last_scene_prompt_json") if isinstance(state_snapshot, dict) else None
                scene_image_payload = None

                if generation_success:
                    scene_image_payload = {
                        "url": image_data.get("url"),
                        "prompt": image_data.get("prompt"),
                        "style": image_data.get("style", "default"),
                        "width": image_data.get("width"),
                        "height": image_data.get("height"),
                        "cached": image_data.get("cached", False),
                        "protagonist_reference_usage": usage,
                    }
                    if prompt_json is not None:
                        scene_image_payload["prompt_json"] = prompt_json
                    save_payload = {
                        "scene": scene_text,
                        "sceneId": scene_payload.get("scene_id"),
                        "scene_image": scene_image_payload,
                    }
                    json_path, image_path = save_segment_to_folder(
                        REPO_ROOT,
                        run_game_id,
                        segment_index,
                        save_payload,
                        state_snapshot,
                        theme_item_id=theme_id,
                        option_text=str(scene_payload.get("option") or row.get("selected_option") or ""),
                        parent_scene_id=scene_payload.get("parent_scene_id") or "initial",
                        option_index=int(scene_payload.get("option_id") or 0),
                        output_root=group_output_root,
                        experiment_subdir="DN-experiment-2.0/ablations/protagonist_ref_ablation/results",
                    )
                    saved_json_path = str(json_path)
                    saved_image_path = str(image_path) if image_path else ""
                    previous_scene_image = dict(scene_image_payload)
                    previous_scene_text = scene_text
                else:
                    error_message = error_message or "generate_scene_image returned no url"

                generation_record = {
                    "run_id": run_id,
                    "dataset_id": row.get("dataset_id"),
                    "dataset_variant": row.get("dataset_variant", "general"),
                    "protagonist_ref_group": group_id,
                    "group_label": group["label"],
                    "theme_id": row.get("theme_id"),
                    "theme": row.get("theme"),
                    "base_game_id": base_game_id,
                    "run_game_id": run_game_id,
                    "segment_index": segment_index,
                    "sample_id": sample_id,
                    "scene_json_source_path": row.get("scene_json_path"),
                    "state_snapshot_path": row.get("state_snapshot_path"),
                    "difficulty_tags": row.get("difficulty_tags", []),
                    "hard_score": row.get("hard_score", 0),
                    "view_bucket": row.get("view_bucket", "front_or_unspecified"),
                    "protagonist_visible_required": row.get("protagonist_visible_required", True),
                    "prompt_hardening_profile": row.get("prompt_hardening_profile", {}),
                    "expected_protagonist_ref_count": expected_count,
                    "actual_protagonist_ref_count": usage.get("actual_count", 0) if usage else 0,
                    "actual_protagonist_ref_paths": usage.get("actual_paths", []) if usage else [],
                    "generation_success": generation_success,
                    "cached": image_data.get("cached") if generation_success else False,
                    "image_url": image_data.get("url") if generation_success else "",
                    "saved_json_path": saved_json_path,
                    "saved_image_path": saved_image_path,
                    "duration_seconds": duration_seconds,
                    "started_at_utc": start_ts,
                    "ended_at_utc": end_ts,
                    "error_message": error_message,
                    "main_character_wait_seconds": front_wait.get("wait_seconds", 0.0),
                    "main_character_ready": front_wait.get("ready", True),
                    "cache_repair_applied": bool(cache_repair_note),
                }
                generation_rows.append(generation_record)

                protagonist_usage_rows.append(
                    {
                        "run_id": run_id,
                        "protagonist_ref_group": group_id,
                        "theme_id": row.get("theme_id"),
                        "base_game_id": base_game_id,
                        "run_game_id": run_game_id,
                        "segment_index": segment_index,
                        "sample_id": sample_id,
                        "expected_protagonist_ref_count": expected_count,
                        "available_protagonist_ref_count": usage.get("available_count", 0) if usage else 0,
                        "actual_protagonist_ref_count": usage.get("actual_count", 0) if usage else 0,
                        "selection_mode": usage.get("selection_mode", "not_generated") if usage else "not_generated",
                        "view_names": usage.get("view_names", []) if usage else [],
                        "available_protagonist_ref_paths": usage.get("available_paths", []) if usage else [],
                        "actual_protagonist_ref_paths": usage.get("actual_paths", []) if usage else [],
                    }
                )

                updated_dataset_rows.append(
                    {
                        **row,
                        "run_id": run_id,
                        "run_game_id": run_game_id,
                        "actual_protagonist_ref_count": usage.get("actual_count", 0) if usage else 0,
                        "actual_protagonist_ref_paths": usage.get("actual_paths", []) if usage else [],
                        "generated_scene_json_path": saved_json_path,
                        "generated_image_path": saved_image_path,
                        "status": "generated" if generation_success else "generation_failed",
                    }
                )

        export_group_manifests(group_output_root)
        if not args.skip_scoring:
            group_scoring_root = scoring_root / group_id
            group_scoring_root.mkdir(parents=True, exist_ok=True)
            score_group(group_output_root, group_scoring_root, judge_models)
            aggregate_group(group_scoring_root, args.config)
            group_score_rows = read_jsonl(group_scoring_root / "latest_per_game_image_scores.jsonl")
            for score_row in group_score_rows:
                score_row["protagonist_ref_group"] = group_id
            score_rows_all.extend(group_score_rows)

    generation_lookup = {row["sample_id"]: row for row in generation_rows}
    per_sample_rows = aggregate_per_sample(score_rows_all, generation_lookup, dimensions)
    summary_rows = build_group_summary(updated_dataset_rows, generation_rows, per_sample_rows, dimensions)
    comparison_rows = build_group_comparison(summary_rows, dimensions)
    dataset_variant_summary_rows = build_subset_summary(per_sample_rows, dimensions, "dataset_variant")
    view_bucket_summary_rows = build_subset_summary(per_sample_rows, dimensions, "view_bucket")
    failure_rows = build_failure_cases(generation_rows, per_sample_rows, dimensions)

    config_snapshot = {
        "run_id": run_id,
        "dataset_variant": dataset_variant,
        "generated_at_utc": utc_now().isoformat(),
        "dataset_manifest_path": str(dataset_manifest_path),
        "judge_models": judge_models,
        "skip_scoring": args.skip_scoring,
        "max_samples": args.max_samples,
        "smoke_segments": args.smoke_segments,
        "group_specs": group_specs,
        "config_path": str(args.config),
    }

    dataset_manifest_out = analysis_root / "dataset_manifest.jsonl"
    generation_runs_out = analysis_root / "generation_runs.jsonl"
    usage_out = analysis_root / "protagonist_reference_usage.jsonl"
    per_sample_out = analysis_root / "per_sample_results.jsonl"
    group_summary_out = analysis_root / "group_summary.json"
    group_comparison_out = analysis_root / "group_comparison.json"
    dataset_variant_summary_out = analysis_root / "dataset_variant_summary.json"
    view_bucket_summary_out = analysis_root / "view_bucket_summary.json"
    failure_out = analysis_root / "failure_cases.jsonl"
    workbook_out = analysis_root / "protagonist_ref_ablation_results.xlsx"

    write_jsonl(dataset_manifest_out, updated_dataset_rows)
    write_jsonl(generation_runs_out, generation_rows)
    write_jsonl(usage_out, protagonist_usage_rows)
    write_jsonl(per_sample_out, per_sample_rows)
    write_json(group_summary_out, summary_rows)
    write_json(group_comparison_out, comparison_rows)
    write_json(dataset_variant_summary_out, dataset_variant_summary_rows)
    write_json(view_bucket_summary_out, view_bucket_summary_rows)
    write_jsonl(failure_out, failure_rows)
    write_json(analysis_root / "config_snapshot.json", config_snapshot)
    if not args.no_xlsx:
        write_workbook(
            workbook_out,
            {
                "dataset_manifest": updated_dataset_rows,
                "generation_runs": generation_rows,
                "protagonist_reference_usage": protagonist_usage_rows,
                "per_sample_results": per_sample_rows,
                "group_summary": summary_rows,
                "group_comparison": comparison_rows,
                "dataset_variant_summary": dataset_variant_summary_rows,
                "view_bucket_summary": view_bucket_summary_rows,
                "failure_cases": failure_rows,
                "config_snapshot": flatten_dict(config_snapshot),
            },
        )
        copy_latest(workbook_out, variant_output_dir / ("latest_results.xlsx" if dataset_variant == "general" else f"latest_{dataset_variant}_results.xlsx"))
    copy_latest(group_summary_out, variant_output_dir / ("latest_group_summary.json" if dataset_variant == "general" else f"latest_{dataset_variant}_group_summary.json"))
    copy_latest(dataset_manifest_out, variant_output_dir / ("latest_dataset_manifest_with_results.jsonl" if dataset_variant == "general" else f"latest_{dataset_variant}_dataset_manifest_with_results.jsonl"))

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "generated_root": str(generated_root),
        "analysis_root": str(analysis_root),
        "workbook_path": str(workbook_out) if not args.no_xlsx else "",
        "group_count": len(group_specs),
        "generation_row_count": len(generation_rows),
        "per_sample_row_count": len(per_sample_rows),
        "failure_row_count": len(failure_rows),
    }
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

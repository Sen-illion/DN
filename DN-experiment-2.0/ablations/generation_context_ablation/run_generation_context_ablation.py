from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import Workbook

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

from src.image.api_providers import generate_scene_image

from common import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SOURCE_EXPERIMENT_ROOT,
    DEFAULT_THEMES_PATH,
    append_sheet,
    as_text,
    build_dataset_manifest,
    discover_source_games,
    flatten_task,
    load_config,
    load_json,
    make_key_value_rows,
    now_utc_iso,
    write_dataset_artifacts,
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


def parse_theme_ids(raw: str) -> List[int]:
    values: List[int] = []
    for part in (raw or "").split(","):
        text = part.strip()
        if not text:
            continue
        values.append(int(text))
    return sorted(set(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the image-generation context ablation experiment.")
    parser.add_argument("--scale", type=str, default="pilot", help="Dataset scale preset: pilot / standard / full.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for dataset selection.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Ablation config JSON path.")
    parser.add_argument(
        "--scoring-config",
        type=Path,
        default=DEFAULT_SCORING_CONFIG_PATH,
        help="Scoring config JSON path used by the reused multiview aggregation logic.",
    )
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=DEFAULT_SOURCE_EXPERIMENT_ROOT,
        help="Root directory containing source theme_* experiment folders.",
    )
    parser.add_argument(
        "--themes-file",
        type=Path,
        default=DEFAULT_THEMES_PATH,
        help="Path to game_themes_100.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for run artifacts.",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=None,
        help="Optional pre-built dataset_manifest.json. If omitted, the runner builds one first.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Optional run name. Defaults to a timestamped name derived from scale and seed.",
    )
    parser.add_argument(
        "--judge-models",
        type=str,
        default="",
        help="Comma-separated judge models for reused multiview scoring.",
    )
    parser.add_argument("--skip-scoring", action="store_true", help="Skip the judge-model scoring stage.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare manifests and plan generation without calling image APIs.")
    parser.add_argument("--max-games", type=int, default=0, help="Optional override for selected game count.")
    parser.add_argument(
        "--max-eval-segments",
        type=int,
        default=0,
        help="Optional override for evaluated segment count per game.",
    )
    parser.add_argument(
        "--theme-ids",
        type=str,
        default="",
        help="Optional comma-separated theme IDs, e.g. 1,3,4.",
    )
    return parser.parse_args()


def parse_models(models_csv: str) -> List[str]:
    return [part.strip() for part in (models_csv or "").split(",") if part.strip()]


def build_run_name(scale: str, seed: int, custom_name: str) -> str:
    if custom_name.strip():
        return custom_name.strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"generation_context_ablation_{scale}_seed{seed}_{timestamp}"


def resolve_local_image(path_or_url: str) -> Optional[Path]:
    raw = as_text(path_or_url).strip()
    if not raw:
        return None
    if raw.startswith("/image_cache/") or raw.startswith("image_cache/"):
        cache_name = Path(raw.replace("\\", "/")).name
        candidates = [
            REPO_ROOT / "image_cache" / cache_name,
            Path.cwd() / "image_cache" / cache_name,
            Path.home() / "image_cache" / cache_name,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None
    candidate = Path(raw)
    if candidate.is_file():
        return candidate.resolve()
    return None


def materialize_image(image_result: Dict[str, Any], destination_path: Path) -> Optional[Path]:
    local_source = resolve_local_image(as_text(image_result.get("url")))
    if local_source is None or not local_source.is_file():
        return None
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_source, destination_path)
    return destination_path.resolve()


def build_previous_scene_payload(image_path: Optional[Path], prompt: str, scene_text: str) -> Dict[str, Any]:
    if image_path is None:
        return {}
    return {
        "url": str(image_path),
        "image_url": str(image_path),
        "prompt": prompt,
        "scene_text": scene_text,
    }


def image_style_label(image_style: Dict[str, Any]) -> str:
    if not isinstance(image_style, dict):
        return "default"
    style_type = as_text(image_style.get("type")).strip() or "default"
    subtype = as_text(image_style.get("subtype")).strip()
    return f"{style_type}/{subtype}" if subtype else style_type


def build_naive_t2i_prompt(*, theme: str, image_style: Dict[str, Any], scene_text: str) -> str:
    """Weak baseline: current scene only, no memory and no source rich prompt."""
    return (
        "Generate one story scene illustration.\n"
        f"Game theme: {theme}\n"
        f"Image style key: {image_style_label(image_style)}\n"
        f"Current scene text: {scene_text}\n"
        "Use only the current scene. Do not infer continuity from previous images, "
        "reference images, prior prompts, or hidden game state. No text, no watermark, "
        "no symbols, no garbled characters, no words."
    )


def build_visual_bible_text(*, theme: str, image_style: Dict[str, Any], source_first_prompt: str) -> str:
    """Text-only memory baseline anchored by the first segment prompt from the same source game."""
    first_prompt = as_text(source_first_prompt).strip()
    if len(first_prompt) > 1800:
        first_prompt = first_prompt[:1800]
    return (
        f"Game theme: {theme}\n"
        f"Image style key: {image_style_label(image_style)}\n"
        "Fixed visual bible for all generated images in this game:\n"
        "- Keep the same protagonist identity, apparent age, body type, outfit logic, and key props across all scenes.\n"
        "- Keep the same world visual language, palette, lighting logic, camera language, and art style.\n"
        "- Only change pose, action, expression, local environment, and story-specific damage/status when the current scene requires it.\n"
        f"- Visual anchor from the first source prompt: {first_prompt or '(none)'}"
    )


def build_visual_bible_prompt(
    *,
    theme: str,
    image_style: Dict[str, Any],
    scene_text: str,
    source_first_prompt: str,
) -> str:
    """Strong no-GPU baseline: text-only visual memory plus current scene."""
    return (
        build_visual_bible_text(theme=theme, image_style=image_style, source_first_prompt=source_first_prompt)
        + "\n\nCurrent scene to illustrate:\n"
        + as_text(scene_text).strip()
        + "\n\nUse the visual bible as text memory only. Do not use any image reference. "
        "No text, no watermark, no symbols, no garbled characters, no words."
    )


def build_global_state(
    *,
    run_game_id: str,
    theme: str,
    image_style: Dict[str, Any],
    scene_text: str,
    prompt_text: str,
    prompt_json: Any,
    source_first_prompt: str,
    group_name: str,
    group_cfg: Dict[str, Any],
    runtime_cfg: Dict[str, Any],
    previous_image_path: Optional[Path],
    previous_prompt: str,
    previous_scene_text: str,
) -> Dict[str, Any]:
    prompt_strategy = as_text(group_cfg.get("prompt_strategy") or "provided").strip().lower()
    use_previous_image = bool(group_cfg.get("use_previous_image", False))
    minimal_prompt = as_text(runtime_cfg.get("minimal_prompt_instruction")).strip()

    overrides: Dict[str, Any] = {
        "context_mode": group_name,
        "prompt_strategy": prompt_strategy,
        "disable_previous_scene_reference": not use_previous_image,
    }
    if prompt_strategy == "provided":
        overrides["prompt_override"] = prompt_text
        if prompt_json is not None:
            overrides["prompt_json_override"] = prompt_json
    elif prompt_strategy == "scene_only":
        overrides["prompt_strategy"] = "provided"
        overrides["prompt_override"] = build_naive_t2i_prompt(
            theme=theme,
            image_style=image_style,
            scene_text=scene_text,
        )
    elif prompt_strategy == "visual_bible":
        overrides["prompt_strategy"] = "provided"
        overrides["prompt_override"] = build_visual_bible_prompt(
            theme=theme,
            image_style=image_style,
            scene_text=scene_text,
            source_first_prompt=source_first_prompt,
        )
    elif prompt_strategy == "minimal_base":
        overrides["minimal_prompt"] = minimal_prompt

    global_state: Dict[str, Any] = {
        "game_id": run_game_id,
        "user_theme": theme,
        "image_style": image_style,
        "tone": "normal_ending",
        "core_worldview": {
            "game_style": theme,
            "world_basic_setting": theme,
        },
        "flow_worldline": {},
        "_skip_protagonist_reference": bool(runtime_cfg.get("skip_protagonist_reference", True)),
        "_scene_generation_overrides": overrides,
    }
    if use_previous_image and previous_image_path is not None:
        global_state["_visual_context"] = {
            "sceneId": f"{run_game_id}_prev",
            "previousSceneImage": build_previous_scene_payload(previous_image_path, previous_prompt, previous_scene_text),
            "previousSceneText": previous_scene_text,
        }
    return global_state


def generation_output_paths(run_dir: Path, group_name: str, source_game_id: str, segment_index: int) -> Tuple[Path, Path]:
    group_game_dir = run_dir / "generated" / group_name / source_game_id
    image_path = group_game_dir / f"seg_{segment_index:03d}.png"
    json_path = group_game_dir / f"seg_{segment_index:03d}.json"
    return image_path, json_path


def plan_generation_sequences(tasks: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        grouped[(task["group"], task["game_id"])].append(task)

    plans: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for key, grouped_tasks in grouped.items():
        grouped_tasks.sort(key=lambda item: int(item["segment_index"]))
        max_eval_segment = max(int(task["segment_index"]) for task in grouped_tasks)
        plans[key] = {
            "eval_tasks": grouped_tasks,
            "eval_segment_indexes": [int(task["segment_index"]) for task in grouped_tasks],
            "warmup_segment_indexes": list(range(1, max_eval_segment + 1)),
        }
    return plans


def generation_result_row(
    *,
    task_type: str,
    group_name: str,
    source_game_id: str,
    run_game_id: str,
    theme_id: int,
    theme: str,
    segment_index: int,
    previous_segment_index: Optional[int],
    status: str,
    duration_seconds: float,
    prompt_strategy: str,
    used_previous_image: bool,
    previous_image_source: str,
    generated_image_path: Optional[Path],
    image_url: str,
    used_prompt: str,
    source_prompt: str,
    source_scene: str,
    error_message: str = "",
) -> Dict[str, Any]:
    return {
        "task_type": task_type,
        "group": group_name,
        "theme_id": theme_id,
        "theme": theme,
        "source_game_id": source_game_id,
        "run_game_id": run_game_id,
        "segment_index": segment_index,
        "previous_segment_index": previous_segment_index,
        "status": status,
        "duration_seconds": round(duration_seconds, 4),
        "prompt_strategy": prompt_strategy,
        "used_previous_image": used_previous_image,
        "previous_image_source": previous_image_source,
        "generated_image_path": str(generated_image_path) if generated_image_path else "",
        "image_url": image_url,
        "used_prompt": used_prompt,
        "source_prompt": source_prompt,
        "source_scene": source_scene,
        "error_message": error_message,
    }


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
    average_duration = mean([row["duration_seconds"] for row in successful_generation_rows]) if successful_generation_rows else None
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
        "average_generation_seconds": round(average_duration, 4) if average_duration is not None else None,
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


def build_config_snapshot_rows(
    *,
    args: argparse.Namespace,
    dataset_manifest: Dict[str, Any],
    config: Dict[str, Any],
    scoring_config: Dict[str, Any],
    run_name: str,
    effective_scale: str,
    effective_seed: int,
) -> List[Dict[str, Any]]:
    snapshot = {
        "run_name": run_name,
        "generated_at_utc": now_utc_iso(),
        "scale": effective_scale,
        "seed": effective_seed,
        "dry_run": args.dry_run,
        "skip_scoring": args.skip_scoring,
        "judge_models": args.judge_models,
        "dataset_name": dataset_manifest.get("summary", {}).get("dataset_name"),
        "dataset_summary": dataset_manifest.get("summary", {}),
        "groups": config.get("groups", {}),
        "runtime": config.get("runtime", {}),
        "selection": config.get("selection", {}),
        "scoring_config": scoring_config,
        "image_generation_provider": os.getenv("IMAGE_GENERATION_PROVIDER", ""),
        "image_generation_model": os.getenv("Image_Generation_MODEL", ""),
        "img2img_model": os.getenv("Img2img_MODEL", ""),
    }
    return make_key_value_rows(snapshot)


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


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    if args.dataset_manifest is not None:
        dataset_manifest = load_json(args.dataset_manifest)
        dataset_outputs = {"dataset_manifest_json": args.dataset_manifest}
    else:
        dataset_manifest = build_dataset_manifest(
            scale=args.scale,
            seed=args.seed,
            config=config,
            experiment_root=args.experiment_root,
            themes_path=args.themes_file,
            max_games_override=max(0, int(args.max_games)),
            max_eval_segments_override=max(0, int(args.max_eval_segments)),
            theme_ids_filter=parse_theme_ids(args.theme_ids),
        )
        dataset_outputs = write_dataset_artifacts(dataset_manifest, output_root=args.output_root)

    dataset_tasks = dataset_manifest.get("tasks", [])
    source_games = {game.game_id: game for game in discover_source_games(args.experiment_root, args.themes_file)}
    dataset_summary = dataset_manifest.get("summary", {})
    effective_scale = str(dataset_summary.get("scale") or args.scale)
    try:
        effective_seed = int(dataset_summary.get("seed") if dataset_summary.get("seed") is not None else args.seed)
    except Exception:
        effective_seed = int(args.seed)
    run_name = build_run_name(effective_scale, effective_seed, args.run_name)
    run_dir = args.output_root / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    scoring_config = load_json(args.scoring_config)
    scoring_module = load_module("generation_context_ablation_score_module", SCORE_SCRIPT_PATH)
    aggregate_module = load_module("generation_context_ablation_aggregate_module", AGG_SCRIPT_PATH)

    group_cfgs = config.get("groups", {})
    runtime_cfg = config.get("runtime", {})
    generation_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    group_generation_context: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = defaultdict(dict)

    planned_sequences = plan_generation_sequences(dataset_tasks)

    for (group_name, source_game_id), plan in planned_sequences.items():
        source_game = source_games.get(source_game_id)
        if source_game is None:
            failure_rows.append(
                {
                    "stage": "setup",
                    "group": group_name,
                    "game_id": source_game_id,
                    "segment_index": "",
                    "reason": "source_game_missing",
                    "detail": f"Could not rediscover source game {source_game_id}.",
                }
            )
            continue

        group_cfg = group_cfgs[group_name]
        eval_segment_set = {int(task["segment_index"]) for task in plan["eval_tasks"]}
        run_game_id = f"{source_game_id}__{group_name}__{run_name}"
        generated_chain: Dict[int, Dict[str, Any]] = group_generation_context[(group_name, source_game_id)]

        for segment_index in plan["warmup_segment_indexes"]:
            source_segment = source_game.segments.get(segment_index)
            if source_segment is None:
                failure_rows.append(
                    {
                        "stage": "generation",
                        "group": group_name,
                        "game_id": source_game_id,
                        "segment_index": segment_index,
                        "reason": "source_segment_missing",
                        "detail": f"Missing source segment {segment_index} in {source_game_id}.",
                    }
                )
                continue

            task_type = "eval" if segment_index in eval_segment_set else "warmup"
            prompt_strategy = as_text(group_cfg.get("prompt_strategy") or "provided").strip().lower()
            use_previous_image = bool(group_cfg.get("use_previous_image", False)) and segment_index > 1 and task_type == "eval"
            previous_image_source = "none"
            previous_image_path: Optional[Path] = None
            previous_prompt = ""
            previous_scene_text = ""

            if segment_index > 1 and use_previous_image:
                previous_generated = generated_chain.get(segment_index - 1)
                if previous_generated and previous_generated.get("generated_image_path"):
                    previous_image_path = Path(previous_generated["generated_image_path"])
                    previous_prompt = as_text(previous_generated.get("used_prompt"))
                    previous_scene_text = as_text(previous_generated.get("source_scene"))
                    previous_image_source = "generated_previous_segment"
                else:
                    fallback_previous = source_game.segments.get(segment_index - 1)
                    if fallback_previous and fallback_previous.image_path is not None:
                        previous_image_path = fallback_previous.image_path
                        previous_prompt = fallback_previous.prompt
                        previous_scene_text = fallback_previous.scene
                        previous_image_source = "source_previous_segment_fallback"

            effective_group_name = group_name
            effective_group_cfg = dict(group_cfg)
            if task_type == "warmup":
                effective_group_name = f"{group_name}_warmup_seed"
                effective_group_cfg["prompt_strategy"] = "provided"
                effective_group_cfg["use_previous_image"] = False
                prompt_strategy = "provided"
                use_previous_image = False
                previous_image_source = "none"
                previous_image_path = None
                previous_prompt = ""
                previous_scene_text = ""

            global_state = build_global_state(
                run_game_id=run_game_id,
                theme=source_game.theme,
                image_style=source_game.image_style,
                scene_text=source_segment.scene,
                prompt_text=source_segment.prompt,
                prompt_json=source_segment.prompt_json,
                source_first_prompt=(source_game.segments.get(1).prompt if source_game.segments.get(1) else ""),
                group_name=effective_group_name,
                group_cfg=effective_group_cfg,
                runtime_cfg=runtime_cfg,
                previous_image_path=previous_image_path,
                previous_prompt=previous_prompt,
                previous_scene_text=previous_scene_text,
            )

            dest_image_path, dest_json_path = generation_output_paths(run_dir, group_name, source_game_id, segment_index)
            status = "success"
            generated_image_path: Optional[Path] = None
            image_result: Dict[str, Any] = {}
            error_message = ""
            started = time.perf_counter()

            try:
                if not args.dry_run and dest_image_path.is_file() and dest_json_path.is_file():
                    image_result = (load_json(dest_json_path).get("image_result") or {})
                    generated_image_path = dest_image_path.resolve()
                    status = "success"
                elif args.dry_run:
                    status = "dry_run"
                else:
                    image_result = generate_scene_image(
                        source_segment.scene,
                        global_state,
                        runtime_cfg.get("default_style", "default"),
                        use_cache=bool(runtime_cfg.get("use_cache", True)),
                        cache_key_suffix=f"{run_name}_{group_name}_{source_game_id}_{segment_index:03d}",
                        skip_cache_lookup=bool(runtime_cfg.get("skip_cache_lookup", True)),
                    ) or {}
                    generated_image_path = materialize_image(image_result, dest_image_path)
                    if generated_image_path is None:
                        status = "failed"
                        error_message = "No local generated image was materialized from the provider result."
                    else:
                        payload = {
                            "group": group_name,
                            "source_game_id": source_game_id,
                            "run_game_id": run_game_id,
                            "theme_id": source_game.theme_id,
                            "theme": source_game.theme,
                            "segment_index": segment_index,
                            "task_type": task_type,
                            "source_scene": source_segment.scene,
                            "source_prompt": source_segment.prompt,
                            "image_result": image_result,
                            "generated_image_path": str(generated_image_path),
                            "used_prompt_json": global_state.get("_last_scene_prompt_json"),
                            "generated_at_utc": now_utc_iso(),
                        }
                        write_json(dest_json_path, payload)
            except Exception as exc:
                status = "failed"
                error_message = str(exc)

            duration_seconds = time.perf_counter() - started
            used_prompt = as_text(
                image_result.get("prompt")
                or global_state.get("_scene_generation_overrides", {}).get("prompt_override")
                or runtime_cfg.get("minimal_prompt_instruction")
                or ""
            ).strip()
            generation_row = generation_result_row(
                task_type=task_type,
                group_name=group_name,
                source_game_id=source_game_id,
                run_game_id=run_game_id,
                theme_id=source_game.theme_id,
                theme=source_game.theme,
                segment_index=segment_index,
                previous_segment_index=(segment_index - 1 if segment_index > 1 else None),
                status=status,
                duration_seconds=duration_seconds,
                prompt_strategy=prompt_strategy,
                used_previous_image=use_previous_image,
                previous_image_source=previous_image_source,
                generated_image_path=generated_image_path,
                image_url=as_text(image_result.get("url")).strip(),
                used_prompt=used_prompt,
                source_prompt=source_segment.prompt,
                source_scene=source_segment.scene,
                error_message=error_message,
            )
            generation_rows.append(generation_row)

            if status == "success" and generated_image_path is not None:
                generated_chain[segment_index] = generation_row
            elif status == "failed":
                failure_rows.append(
                    {
                        "stage": "generation",
                        "group": group_name,
                        "game_id": source_game_id,
                        "segment_index": segment_index,
                        "reason": "generation_failed",
                        "detail": error_message,
                    }
                )

    score_rows: List[Dict[str, Any]] = []
    if not args.skip_scoring and not args.dry_run:
        judge_models = parse_models(args.judge_models)
        if judge_models:
            scoring_module.load_env()
            client = scoring_module.OpenAI()
            for task in dataset_tasks:
                group_name = task["group"]
                source_game_id = task["game_id"]
                segment_index = int(task["segment_index"])
                generated_chain = group_generation_context.get((group_name, source_game_id), {})
                current_generated = generated_chain.get(segment_index)
                previous_generated = generated_chain.get(segment_index - 1)
                if not current_generated or not current_generated.get("generated_image_path"):
                    failure_rows.append(
                        {
                            "stage": "scoring",
                            "group": group_name,
                            "game_id": source_game_id,
                            "segment_index": segment_index,
                            "reason": "missing_generated_image",
                            "detail": "Current generated image missing; sample skipped in scoring.",
                        }
                    )
                    continue

                current_image_path = Path(current_generated["generated_image_path"])
                prev_image_path = (
                    Path(previous_generated["generated_image_path"])
                    if previous_generated and previous_generated.get("generated_image_path")
                    else None
                )
                sample = scoring_module.Sample(
                    game_id=source_game_id,
                    theme_item_id=task["theme_id"],
                    segment_index=segment_index,
                    sample_id=task["sample_id"],
                    image_path=current_image_path,
                    prompt_text=as_text(current_generated.get("used_prompt")).strip(),
                    scene_text=as_text(task.get("source_scene")).strip(),
                    prev_image_path=prev_image_path,
                    prev_scene_text=as_text(task.get("source_previous_scene")).strip(),
                )

                for judge_model in judge_models:
                    try:
                        normalized = scoring_module.score_sample(client, judge_model, sample)
                        row = {
                            "group": group_name,
                            "theme_id": task["theme_id"],
                            "theme": task["theme"],
                            "source_game_id": source_game_id,
                            "sample_id": task["sample_id"],
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
                        score_rows.append(row)
                    except Exception as exc:
                        failure_rows.append(
                            {
                                "stage": "scoring",
                                "group": group_name,
                                "game_id": source_game_id,
                                "segment_index": segment_index,
                                "reason": "judge_failed",
                                "detail": f"{judge_model}: {exc}",
                            }
                        )
        else:
            failure_rows.append(
                {
                    "stage": "scoring",
                    "group": "",
                    "game_id": "",
                    "segment_index": "",
                    "reason": "judge_models_missing",
                    "detail": "No judge models were provided; scoring was skipped.",
                }
            )

    planned_eval_by_group: Dict[str, int] = defaultdict(int)
    for task in dataset_tasks:
        planned_eval_by_group[task["group"]] += 1

    group_summaries = [
        build_group_summary(
            group_name=group_name,
            planned_eval_count=planned_eval_by_group[group_name],
            generation_rows=generation_rows,
            score_rows=score_rows,
            scoring_module=scoring_module,
            aggregate_module=aggregate_module,
            scoring_config=scoring_config,
        )
        for group_name in config.get("groups", {}).keys()
    ]
    group_comparison = build_group_comparison(group_summaries)

    dataset_task_rows = [flatten_task(task) for task in dataset_tasks]
    config_snapshot_rows = build_config_snapshot_rows(
        args=args,
        dataset_manifest=dataset_manifest,
        config=config,
        scoring_config=scoring_config,
        run_name=run_name,
        effective_scale=effective_scale,
        effective_seed=effective_seed,
    )

    write_json(run_dir / "dataset_manifest.json", dataset_manifest)
    write_jsonl(run_dir / "generation_runs.jsonl", generation_rows)
    write_jsonl(run_dir / "per_sample_results.jsonl", score_rows)
    write_json(run_dir / "group_summary.json", group_summaries)
    write_json(run_dir / "group_comparison.json", group_comparison)
    write_json(run_dir / "failure_cases.json", failure_rows)

    for group_name in config.get("groups", {}).keys():
        group_generation_rows = [row for row in generation_rows if row.get("group") == group_name]
        group_score_rows = [row for row in score_rows if row.get("group") == group_name]
        group_summary = next((row for row in group_summaries if row.get("group") == group_name), None)
        group_dir = run_dir / "groups" / group_name
        group_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(group_dir / "generation_results.jsonl", group_generation_rows)
        write_jsonl(group_dir / "score_results.jsonl", group_score_rows)
        write_json(group_dir / "summary.json", group_summary or {"group": group_name})

    workbook_path = run_dir / "generation_context_ablation_results.xlsx"
    build_workbook(
        workbook_path=workbook_path,
        dataset_tasks=dataset_task_rows,
        generation_rows=generation_rows,
        score_rows=score_rows,
        group_summaries=group_summaries,
        group_comparison=group_comparison,
        failure_rows=failure_rows,
        config_snapshot_rows=config_snapshot_rows,
    )

    print(f"run_dir={run_dir}")
    print(f"dataset_manifest_json={dataset_outputs.get('dataset_manifest_json')}")
    print(f"workbook={workbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

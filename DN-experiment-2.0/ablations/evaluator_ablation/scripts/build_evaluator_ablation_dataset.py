from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from shared import (
    ABLATION_RESULTS_DIR,
    DEFAULT_JUDGE_GROUPS,
    DN_EXPERIMENT_ROOT,
    REPO_ROOT,
    THEMES_JSON,
    discover_manifest_paths,
    export_workbook_payload,
    load_theme_catalog,
    read_json,
    resolve_repo_path,
    safe_text,
    utc_now,
    write_json,
    write_jsonl,
)

DEFAULT_CONFIG = REPO_ROOT / "DN-experiment-2.0" / "ablations" / "evaluator_ablation" / "configs" / "evaluator_ablation_config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reproducible dataset manifest for evaluator ablation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Config JSON for preset sizes and paths.")
    parser.add_argument("--themes-json", type=Path, default=THEMES_JSON, help="Path to game_themes_100.json.")
    parser.add_argument("--experiment-root", type=Path, default=DN_EXPERIMENT_ROOT, help="DN experiment root containing theme_* folders.")
    parser.add_argument("--output-dir", type=Path, default=ABLATION_RESULTS_DIR, help="Directory for manifest outputs.")
    parser.add_argument("--size", type=str, default="standard", help="Dataset size preset: pilot / standard / full.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed override.")
    parser.add_argument("--max-themes", type=int, default=None, help="Optional cap on selected themes.")
    parser.add_argument("--max-games", type=int, default=None, help="Optional cap on selected games.")
    parser.add_argument("--segments-per-game", type=int, default=None, help="Optional cap on selected segments per game.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional cap on selected samples.")
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return read_json(path)


def resolve_size_config(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    presets = (config.get("dataset_presets") or {})
    preset = dict(presets.get(args.size, {}))
    seed = args.seed if args.seed is not None else config.get("seed", 20260425)
    result = {
        "size": args.size,
        "seed": int(seed),
        "max_themes": args.max_themes if args.max_themes is not None else int(preset.get("max_themes", 0) or 0),
        "max_games": args.max_games if args.max_games is not None else int(preset.get("max_games", 0) or 0),
        "segments_per_game": args.segments_per_game if args.segments_per_game is not None else int(preset.get("segments_per_game", 0) or 0),
        "max_samples": args.max_samples if args.max_samples is not None else int(preset.get("max_samples", 0) or 0),
    }
    return result


def build_inventory(theme_catalog: Dict[int, Dict[str, Any]], experiment_root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    manifest_paths = discover_manifest_paths(experiment_root)
    manifests_by_theme: Dict[int, List[Path]] = defaultdict(list)
    for manifest_path in manifest_paths:
        try:
            manifest = read_json(manifest_path)
            theme_id = int(manifest.get("theme_item_id") or 0)
        except Exception:
            continue
        manifests_by_theme[theme_id].append(manifest_path)

    rows: List[Dict[str, Any]] = []
    theme_summary: List[Dict[str, Any]] = []
    diagnostics: Dict[str, Any] = {
        "total_themes_in_catalog": len(theme_catalog),
        "discovered_manifest_files": len(manifest_paths),
        "themes_with_manifest": 0,
        "themes_without_manifest": 0,
        "available_sample_candidates": 0,
        "unavailable_sample_candidates": 0,
    }

    for theme_id in sorted(theme_catalog):
        theme_item = theme_catalog[theme_id]
        theme_text = theme_item.get("theme", "")
        style_label = theme_item.get("style_label_zh", "")
        manifests = manifests_by_theme.get(theme_id, [])
        if not manifests:
            rows.append(
                {
                    "theme_id": theme_id,
                    "theme": theme_text,
                    "style_label_zh": style_label,
                    "game_id": "",
                    "segment_index": "",
                    "sample_id": f"theme_{theme_id:03d}_missing",
                    "image_path": "",
                    "image_path_repo_relative": "",
                    "is_available": False,
                    "selected": False,
                    "selection_reason": "filtered_out:no_image_manifest",
                    "availability_reason": "missing_image_manifest",
                    "source_manifest_path": "",
                    "source_segment_json_path": "",
                    "prompt_text": "",
                    "scene_text": "",
                    "prev_scene_text": "",
                    "prev_image_path": "",
                }
            )
            theme_summary.append(
                {
                    "theme_id": theme_id,
                    "theme": theme_text,
                    "style_label_zh": style_label,
                    "game_count": 0,
                    "candidate_samples": 0,
                    "available_samples": 0,
                    "status": "missing_manifest",
                    "notes": "No *_image_paths.json found for this theme.",
                }
            )
            diagnostics["themes_without_manifest"] += 1
            continue

        diagnostics["themes_with_manifest"] += 1
        theme_game_count = 0
        theme_candidate_samples = 0
        theme_available_samples = 0

        for manifest_path in manifests:
            manifest = read_json(manifest_path)
            game_id = str(manifest.get("game_id") or manifest_path.parent.name)
            theme_game_count += 1
            segments = manifest.get("segments") or []
            if not segments:
                rows.append(
                    {
                        "theme_id": theme_id,
                        "theme": theme_text,
                        "style_label_zh": style_label,
                        "game_id": game_id,
                        "segment_index": "",
                        "sample_id": f"{game_id}_missing_segments",
                        "image_path": "",
                        "image_path_repo_relative": "",
                        "is_available": False,
                        "selected": False,
                        "selection_reason": "filtered_out:manifest_has_no_segments",
                        "availability_reason": "manifest_has_no_segments",
                        "source_manifest_path": str(manifest_path),
                        "source_segment_json_path": "",
                        "prompt_text": "",
                        "scene_text": "",
                        "prev_scene_text": "",
                        "prev_image_path": "",
                    }
                )
                continue

            prev_scene_text = ""
            prev_image_path = ""
            for segment in segments:
                seg_index = int(segment.get("segment_index") or 0)
                sample_id = f"{game_id}_seg_{seg_index:03d}"
                image_rel = str(segment.get("image_path_repo_relative") or "")
                image_path = resolve_repo_path(image_rel) if image_rel else None
                segment_json_path = manifest_path.parent / str(segment.get("json_file") or "")
                segment_payload = read_json(segment_json_path) if segment_json_path.is_file() else {}
                prompt_text = safe_text(segment_payload.get("prompt"), max_len=2000)
                scene_text = safe_text(segment_payload.get("scene"), max_len=2000)
                manifest_exists_flag = bool(segment.get("exists"))
                file_exists_flag = bool(image_path and image_path.is_file())
                is_available = manifest_exists_flag and file_exists_flag
                availability_reason = "available_existing_image" if is_available else "missing_or_unresolved_image"
                row = {
                    "theme_id": theme_id,
                    "theme": theme_text,
                    "style_label_zh": style_label,
                    "game_id": game_id,
                    "segment_index": seg_index,
                    "sample_id": sample_id,
                    "image_path": str(image_path) if image_path else "",
                    "image_path_repo_relative": image_rel,
                    "is_available": is_available,
                    "selected": False,
                    "selection_reason": "candidate_not_selected_yet" if is_available else "filtered_out:unavailable_image",
                    "availability_reason": availability_reason,
                    "source_manifest_path": str(manifest_path),
                    "source_segment_json_path": str(segment_json_path) if segment_json_path.is_file() else "",
                    "prompt_text": prompt_text,
                    "scene_text": scene_text,
                    "prev_scene_text": prev_scene_text,
                    "prev_image_path": prev_image_path,
                }
                rows.append(row)
                theme_candidate_samples += 1
                if is_available:
                    theme_available_samples += 1
                    diagnostics["available_sample_candidates"] += 1
                    prev_scene_text = scene_text
                    prev_image_path = str(image_path) if image_path else ""
                else:
                    diagnostics["unavailable_sample_candidates"] += 1

        theme_summary.append(
            {
                "theme_id": theme_id,
                "theme": theme_text,
                "style_label_zh": style_label,
                "game_count": theme_game_count,
                "candidate_samples": theme_candidate_samples,
                "available_samples": theme_available_samples,
                "status": "available" if theme_available_samples else "manifest_but_no_available_images",
                "notes": "",
            }
        )

    diagnostics["themes_with_available_samples"] = sum(1 for row in theme_summary if row["available_samples"] > 0)
    diagnostics["themes_without_available_samples"] = sum(1 for row in theme_summary if row["available_samples"] == 0)
    diagnostics["themes_missing_image_ids"] = [row["theme_id"] for row in theme_summary if row["available_samples"] == 0]
    diagnostics["themes_missing_image_texts"] = [row["theme"] for row in theme_summary if row["available_samples"] == 0]
    return rows, theme_summary, diagnostics


def apply_selection(rows: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    rng = random.Random(int(settings["seed"]))
    available_rows = [row for row in rows if row.get("is_available")]
    rows_by_theme: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    rows_by_game: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    theme_by_game: Dict[str, int] = {}

    for row in available_rows:
        theme_id = int(row["theme_id"])
        game_id = str(row["game_id"])
        rows_by_theme[theme_id].append(row)
        rows_by_game[game_id].append(row)
        theme_by_game[game_id] = theme_id

    available_theme_ids = sorted(rows_by_theme)
    shuffled_theme_ids = available_theme_ids[:]
    rng.shuffle(shuffled_theme_ids)

    max_themes = int(settings.get("max_themes") or 0)
    if max_themes > 0:
        selected_theme_ids = shuffled_theme_ids[:max_themes]
    else:
        selected_theme_ids = shuffled_theme_ids
    selected_theme_set = set(selected_theme_ids)

    selected_games: List[str] = []
    for theme_id in selected_theme_ids:
        game_ids = sorted({str(row["game_id"]) for row in rows_by_theme[theme_id]})
        rng.shuffle(game_ids)
        selected_games.extend(game_ids)

    max_games = int(settings.get("max_games") or 0)
    if max_games > 0:
        selected_games = selected_games[:max_games]
    selected_game_set = set(selected_games)

    segments_per_game = int(settings.get("segments_per_game") or 0)
    selected_sample_ids: List[str] = []
    segment_remainder_ids: set[str] = set()
    for game_id in selected_games:
        candidates = rows_by_game[game_id][:]
        candidates.sort(key=lambda item: (int(item.get("segment_index") or 0), str(item.get("sample_id"))))
        rng.shuffle(candidates)
        if segments_per_game > 0:
            chosen = candidates[:segments_per_game]
            skipped = candidates[segments_per_game:]
        else:
            chosen = candidates
            skipped = []
        selected_sample_ids.extend(str(item["sample_id"]) for item in chosen)
        segment_remainder_ids.update(str(item["sample_id"]) for item in skipped)

    max_samples = int(settings.get("max_samples") or 0)
    sample_quota_remainder_ids: set[str] = set()
    if max_samples > 0 and len(selected_sample_ids) > max_samples:
        keep_ids = selected_sample_ids[:max_samples]
        sample_quota_remainder_ids = set(selected_sample_ids[max_samples:])
        selected_sample_ids = keep_ids

    selected_sample_set = set(selected_sample_ids)

    for row in rows:
        if not row.get("is_available"):
            continue
        sample_id = str(row["sample_id"])
        theme_id = int(row["theme_id"])
        game_id = str(row["game_id"])
        if sample_id in selected_sample_set:
            row["selected"] = True
            row["selection_reason"] = (
                f"selected:size={settings['size']};seed={settings['seed']};"
                f"theme_id={theme_id};game_id={game_id}"
            )
        elif theme_id not in selected_theme_set:
            row["selection_reason"] = "filtered_out:theme_quota"
        elif game_id not in selected_game_set:
            row["selection_reason"] = "filtered_out:game_quota"
        elif sample_id in sample_quota_remainder_ids:
            row["selection_reason"] = "filtered_out:sample_quota"
        elif sample_id in segment_remainder_ids:
            row["selection_reason"] = "filtered_out:segment_quota"
        else:
            row["selection_reason"] = "filtered_out:selection_order"

    selected_rows = [row for row in rows if row.get("selected")]
    target_theme_quota = max_themes if max_themes > 0 else len(available_theme_ids)
    target_game_quota = max_games if max_games > 0 else len({row["game_id"] for row in available_rows})
    selection = {
        "seed": int(settings["seed"]),
        "size": settings["size"],
        "target_theme_quota": target_theme_quota,
        "target_game_quota": target_game_quota,
        "target_segments_per_game": segments_per_game,
        "target_sample_quota": max_samples if max_samples > 0 else len(selected_rows),
        "selected_theme_ids": sorted(selected_theme_set),
        "selected_game_ids": sorted(selected_game_set),
        "selected_sample_ids": selected_sample_ids,
        "selected_theme_count": len({int(row['theme_id']) for row in selected_rows}),
        "selected_game_count": len({str(row['game_id']) for row in selected_rows}),
        "selected_sample_count": len(selected_rows),
        "available_theme_count": len(available_theme_ids),
        "available_game_count": len(rows_by_game),
        "available_sample_count": len(available_rows),
        "sample_shortfall": max(0, (max_samples or len(selected_rows)) - len(selected_rows)),
    }
    return selection


def make_run_metadata(config: Dict[str, Any], settings: Dict[str, Any], selection: Dict[str, Any], diagnostics: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_paths = config.get("source_paths") or {}
    rows = [
        {"key": "generated_at_utc", "value": utc_now().isoformat()},
        {"key": "size", "value": settings["size"]},
        {"key": "seed", "value": settings["seed"]},
        {"key": "max_themes", "value": settings["max_themes"]},
        {"key": "max_games", "value": settings["max_games"]},
        {"key": "segments_per_game", "value": settings["segments_per_game"]},
        {"key": "max_samples", "value": settings["max_samples"]},
        {"key": "themes_json", "value": str(resolve_repo_path(source_paths.get("themes_json")) or THEMES_JSON)},
        {"key": "experiment_root", "value": str(resolve_repo_path(source_paths.get("experiment_root")) or DN_EXPERIMENT_ROOT)},
        {"key": "available_themes", "value": selection["available_theme_count"]},
        {"key": "available_games", "value": selection["available_game_count"]},
        {"key": "available_samples", "value": selection["available_sample_count"]},
        {"key": "selected_themes", "value": selection["selected_theme_count"]},
        {"key": "selected_games", "value": selection["selected_game_count"]},
        {"key": "selected_samples", "value": selection["selected_sample_count"]},
        {"key": "themes_without_available_samples", "value": diagnostics["themes_without_available_samples"]},
        {"key": "judge_group_count", "value": len(config.get("judge_groups") or DEFAULT_JUDGE_GROUPS)},
    ]
    return rows


def build_diagnostics_rows(theme_summary: Iterable[Dict[str, Any]], diagnostics: Dict[str, Any], selection: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = [
        {"section": "inventory", "metric": "total_themes_in_catalog", "value": diagnostics["total_themes_in_catalog"], "notes": "Loaded from game_themes_100.json"},
        {"section": "inventory", "metric": "discovered_manifest_files", "value": diagnostics["discovered_manifest_files"], "notes": "Count of *_image_paths.json files found under DN-experiment-2.0/theme_*"},
        {"section": "inventory", "metric": "themes_with_manifest", "value": diagnostics["themes_with_manifest"], "notes": "Themes with at least one image manifest"},
        {"section": "inventory", "metric": "themes_without_manifest", "value": diagnostics["themes_without_manifest"], "notes": "Themes missing image manifests"},
        {"section": "inventory", "metric": "themes_with_available_samples", "value": diagnostics["themes_with_available_samples"], "notes": "Themes with at least one reusable image sample"},
        {"section": "inventory", "metric": "available_sample_candidates", "value": diagnostics["available_sample_candidates"], "notes": "Reusable images discovered from existing generation outputs"},
        {"section": "selection", "metric": "selected_theme_count", "value": selection["selected_theme_count"], "notes": f"Preset size={selection['size']}"},
        {"section": "selection", "metric": "selected_game_count", "value": selection["selected_game_count"], "notes": "Games included in this evaluator-ablation dataset"},
        {"section": "selection", "metric": "selected_sample_count", "value": selection["selected_sample_count"], "notes": "Samples selected for downstream scoring/comparison"},
        {"section": "selection", "metric": "sample_shortfall", "value": selection["sample_shortfall"], "notes": "Shortfall vs requested max_samples (0 means quota met or not requested)"},
    ]
    missing_themes = [theme for theme in theme_summary if theme["available_samples"] == 0]
    for theme in missing_themes:
        rows.append(
            {
                "section": "missing_theme",
                "metric": f"theme_{int(theme['theme_id']):03d}",
                "value": theme["theme"],
                "notes": theme["status"],
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    size_settings = resolve_size_config(config, args)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    theme_catalog = load_theme_catalog(args.themes_json)
    rows, theme_summary, diagnostics = build_inventory(theme_catalog, args.experiment_root)
    selection = apply_selection(rows, size_settings)
    selected_rows = [row for row in rows if row.get("selected")]
    diagnostics_rows = build_diagnostics_rows(theme_summary, diagnostics, selection)
    run_metadata = make_run_metadata(config, size_settings, selection, diagnostics)

    manifest_json = output_dir / "latest_dataset_manifest.json"
    manifest_jsonl = output_dir / "latest_dataset_manifest.jsonl"
    summary_json = output_dir / "latest_dataset_summary.json"
    workbook_path = output_dir / "latest_dataset_manifest.xlsx"

    manifest_payload = {
        "generated_at_utc": utc_now().isoformat(),
        "experiment_name": config.get("experiment_name", "evaluator_ablation"),
        "selection": selection,
        "dataset_manifest": rows,
        "selected_samples": selected_rows,
        "theme_summary": theme_summary,
        "diagnostics": diagnostics,
        "judge_groups": config.get("judge_groups") or DEFAULT_JUDGE_GROUPS,
    }
    summary_payload = {
        "generated_at_utc": utc_now().isoformat(),
        "manifest_json": str(manifest_json),
        "manifest_jsonl": str(manifest_jsonl),
        "workbook_path": str(workbook_path),
        "selection": selection,
        "diagnostics": diagnostics,
    }
    workbook_payload_obj = {
        "mode": "dataset",
        "dataset_manifest": rows,
        "run_metadata": run_metadata,
        "theme_summary": theme_summary,
        "diagnostics": diagnostics_rows,
    }

    write_json(manifest_json, manifest_payload)
    write_jsonl(manifest_jsonl, rows)
    write_json(summary_json, summary_payload)
    export_workbook_payload("dataset", workbook_payload_obj, workbook_path)

    print(
        {
            "manifest_json": str(manifest_json),
            "manifest_jsonl": str(manifest_jsonl),
            "selected_sample_count": len(selected_rows),
            "selected_theme_count": selection["selected_theme_count"],
            "themes_without_available_samples": diagnostics["themes_without_available_samples"],
            "workbook_path": str(workbook_path),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

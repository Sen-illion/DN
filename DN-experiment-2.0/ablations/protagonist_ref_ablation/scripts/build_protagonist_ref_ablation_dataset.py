from __future__ import annotations

import argparse
import importlib.util
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    THEMES_JSON,
    copy_latest,
    flatten_dict,
    get_group_specs,
    load_config,
    load_theme_catalog,
    read_json,
    resolve_size_settings,
    safe_text,
    strip_state_for_dataset,
    utc_now,
    utc_timestamp,
    write_json,
    write_jsonl,
    write_workbook,
)

from src.characters.paths import generate_game_id
from src.llm.global_gen import llm_generate_global
from src.story.options import _generate_single_option_text_only

_EXPERIMENT_SAVE = REPO_ROOT / "DN-experiment" / "experiment_save.py"
_spec = importlib.util.spec_from_file_location("dn_experiment_save", _EXPERIMENT_SAVE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to load {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder
experiment_dir_name = _save_mod.experiment_dir_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build protagonist reference ablation datasets.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Config JSON path.")
    parser.add_argument("--themes-json", type=Path, default=THEMES_JSON, help="Path to game_themes_100.json.")
    parser.add_argument("--output-dir", type=Path, default=DATASETS_DIR, help="Dataset output root.")
    parser.add_argument("--size", type=str, default="standard", help="Dataset size preset: pilot / standard / full.")
    parser.add_argument(
        "--dataset-variant",
        choices=["general", "hard_identity"],
        default="general",
        help="Dataset construction variant. hard_identity keeps the same 0/1/3 groups but hardens scene prompts.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed override.")
    parser.add_argument("--max-themes", type=int, default=None, help="Override theme count.")
    parser.add_argument("--segments-per-game", type=int, default=None, help="Override segment count.")
    parser.add_argument("--theme-ids", type=str, default="", help="Optional comma-separated theme ids.")
    parser.add_argument("--dataset-name", type=str, default="", help="Optional stable dataset directory name.")
    return parser.parse_args()


HARDENING_PROFILES: List[Dict[str, Any]] = [
    {
        "profile_id": "side_occluded_continuity",
        "difficulty_tags": ["view_side", "occluded_face", "continuity_sensitive"],
        "view_bucket": "side",
        "constraints": [
            "compose the protagonist in a clear side profile or three-quarter side view",
            "partially obscure the face with hair, smoke, clothing, or a foreground prop",
            "preserve continuity-critical outfit, hairstyle, glasses, bag, shoes, and signature props exactly",
        ],
    },
    {
        "profile_id": "back_long_extreme_light",
        "difficulty_tags": ["view_back", "long_shot", "extreme_lighting", "continuity_sensitive"],
        "view_bucket": "back",
        "constraints": [
            "show the protagonist from behind or over the shoulder",
            "use a wide or long shot where the protagonist occupies only about 15-25 percent of the frame",
            "use difficult backlight, night light, neon, fog, firelight, or strong shadow",
            "keep the same outfit silhouette, hairstyle, backpack or carried prop readable despite the distance",
        ],
    },
    {
        "profile_id": "mixed_action_occlusion",
        "difficulty_tags": ["view_mixed", "occluded_face", "action_heavy", "extreme_lighting"],
        "view_bucket": "mixed",
        "constraints": [
            "use a dynamic pose with the head turned away from the camera",
            "partially hide the face behind a door frame, hair, smoke, hand, scarf, or scene prop",
            "add motion, strong shadow, low light, fog, sparks, rain, or reflected light",
            "make clothing details and signature accessories remain stable and identifiable",
        ],
    },
]


def compute_hard_score(tags: List[str]) -> int:
    score = 0
    if "view_side" in tags or "view_back" in tags:
        score += 2
    if "occluded_face" in tags:
        score += 2
    if "long_shot" in tags:
        score += 1
    if "extreme_lighting" in tags:
        score += 1
    if "action_heavy" in tags:
        score += 1
    if "continuity_sensitive" in tags:
        score += 1
    return score


def harden_scene_text(scene_text: str, profile: Dict[str, Any]) -> str:
    constraints = profile.get("constraints") if isinstance(profile.get("constraints"), list) else []
    constraint_text = "; ".join(str(item).strip() for item in constraints if str(item).strip())
    return (
        f"{scene_text}\n\n"
        "[Hard identity evaluation constraints: the protagonist must be visibly present. "
        "Preserve the original narrative meaning, but render the shot as identity-stressful. "
        f"{constraint_text}.]"
    )


def hardening_metadata(segment_index: int) -> Dict[str, Any]:
    profile = HARDENING_PROFILES[(segment_index - 1) % len(HARDENING_PROFILES)]
    tags = list(profile["difficulty_tags"])
    return {
        "dataset_variant": "hard_identity",
        "difficulty_tags": tags,
        "hard_score": compute_hard_score(tags),
        "view_bucket": str(profile["view_bucket"]),
        "protagonist_visible_required": True,
        "prompt_hardening_profile": {
            "profile_id": profile["profile_id"],
            "constraints": list(profile["constraints"]),
        },
    }


def load_theme_items(path: Path) -> Dict[int, Dict[str, Any]]:
    return load_theme_catalog(path)


def select_theme_items(theme_catalog: Dict[int, Dict[str, Any]], settings: Dict[str, Any], theme_ids_csv: str) -> List[Dict[str, Any]]:
    explicit_ids = [int(token.strip()) for token in (theme_ids_csv or "").split(",") if token.strip()]
    if explicit_ids:
        return [theme_catalog[theme_id] for theme_id in explicit_ids if theme_id in theme_catalog]

    rng = random.Random(int(settings["seed"]))
    theme_ids = sorted(theme_catalog.keys())
    rng.shuffle(theme_ids)
    max_themes = int(settings.get("max_themes") or 0)
    if max_themes > 0:
        theme_ids = theme_ids[:max_themes]
    return [theme_catalog[theme_id] for theme_id in theme_ids]


def merge_flow_update(global_state: Dict[str, Any], option_data: Dict[str, Any]) -> None:
    flow_update = option_data.get("flow_update") or {}
    if not isinstance(flow_update, dict):
        return
    flow_worldline = global_state.setdefault("flow_worldline", {})
    if isinstance(flow_worldline, dict):
        flow_worldline.update(flow_update)


def build_segment_rows(
    *,
    dataset_id: str,
    dataset_variant: str,
    dataset_dir: Path,
    theme_item: Dict[str, Any],
    settings: Dict[str, Any],
    group_specs: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    theme_id = int(theme_item["id"])
    theme_text = str(theme_item.get("theme") or "").strip()
    image_style = theme_item.get("image_style") if isinstance(theme_item.get("image_style"), dict) else {}
    style_label = str(theme_item.get("style_label_zh") or "").strip()
    difficulty = str(settings.get("difficulty") or "中等")
    tone_key = str(settings.get("tone_key") or "normal_ending")
    start_option = str(settings.get("start_option") or "开始游戏")
    segment_count = int(settings.get("segments_per_game") or 0)

    game_id = generate_game_id()
    protagonist_attr: Dict[str, Any] = {}
    global_state = llm_generate_global(theme_text, protagonist_attr, difficulty, tone_key)
    if not isinstance(global_state, dict):
        raise RuntimeError(f"Worldview generation failed for theme_id={theme_id}")

    global_state["game_id"] = game_id
    global_state["user_theme"] = theme_text
    global_state["tone"] = tone_key
    if image_style:
        global_state["image_style"] = image_style

    game_dir = dataset_dir / experiment_dir_name(game_id, theme_id)
    game_dir.mkdir(parents=True, exist_ok=True)

    build_context = {
        "dataset_id": dataset_id,
        "dataset_variant": dataset_variant,
        "theme_id": theme_id,
        "theme": theme_text,
        "base_game_id": game_id,
        "protagonist_attr": protagonist_attr,
        "difficulty": difficulty,
        "tone_key": tone_key,
        "image_style": image_style,
        "style_label_zh": style_label,
        "segment_count": segment_count,
        "groups": group_specs,
        "generated_at_utc": utc_now().isoformat(),
    }
    build_context_path = game_dir / f"{game_id}_dataset_game_context.json"
    write_json(build_context_path, build_context)

    dataset_rows: List[Dict[str, Any]] = []
    segment_rows: List[Dict[str, Any]] = []
    parent_scene_id: Any = "initial"
    selected_option = start_option

    for segment_index in range(1, segment_count + 1):
        state_snapshot = strip_state_for_dataset(global_state)
        state_path = game_dir / f"{game_id}_{segment_index:03d}_state.json"
        write_json(state_path, state_snapshot)

        result = _generate_single_option_text_only(0, selected_option, global_state)
        option_data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(option_data, dict):
            raise RuntimeError(f"Text generation failed for {game_id} segment {segment_index}")

        original_scene_text = safe_text(option_data.get("scene"), max_len=1200)
        scene_text = original_scene_text
        hard_meta: Dict[str, Any] = {
            "dataset_variant": dataset_variant,
            "difficulty_tags": [],
            "hard_score": 0,
            "view_bucket": "front_or_unspecified",
            "protagonist_visible_required": True,
            "prompt_hardening_profile": {},
        }
        if dataset_variant == "hard_identity":
            hard_meta = hardening_metadata(segment_index)
            scene_text = harden_scene_text(original_scene_text, hard_meta["prompt_hardening_profile"])
            option_data["scene"] = scene_text

        json_path, _ = save_segment_to_folder(
            REPO_ROOT,
            game_id,
            segment_index,
            option_data,
            global_state,
            theme_item_id=theme_id,
            option_text=selected_option,
            parent_scene_id=parent_scene_id,
            option_index=0,
            output_root=dataset_dir,
            experiment_subdir="DN-experiment-2.0/ablations/protagonist_ref_ablation/datasets",
        )
        segment_payload = read_json(json_path)
        if dataset_variant == "hard_identity":
            segment_payload["scene"] = scene_text
            segment_payload["original_scene"] = original_scene_text
            segment_payload.update(hard_meta)
        segment_payload["state_snapshot_file"] = state_path.name
        segment_payload["dataset_id"] = dataset_id
        segment_payload["dataset_variant"] = dataset_variant
        write_json(json_path, segment_payload)

        next_options = option_data.get("next_options") if isinstance(option_data.get("next_options"), list) else []
        next_option = str(next_options[0]).strip() if next_options else ""
        sample_id = f"{game_id}_seg_{segment_index:03d}"

        segment_rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_variant": dataset_variant,
                "theme_id": theme_id,
                "theme": theme_text,
                "style_label_zh": style_label,
                "base_game_id": game_id,
                "segment_index": segment_index,
                "sample_id": sample_id,
                "scene_json_path": str(json_path),
                "state_snapshot_path": str(state_path),
                "selected_option": selected_option,
                "next_option_for_followup": next_option,
                "scene_preview": scene_text,
                "original_scene_preview": original_scene_text,
                **hard_meta,
            }
        )

        for group in group_specs:
            group_id = group["group_id"]
            dataset_rows.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_variant": dataset_variant,
                    "theme_id": theme_id,
                    "theme": theme_text,
                    "style_label_zh": style_label,
                    "base_game_id": game_id,
                    "segment_index": segment_index,
                    "sample_id": sample_id,
                    "group_sample_id": f"{sample_id}__{group_id}",
                    "protagonist_ref_group": group_id,
                    "group_label": group["label"],
                    "expected_protagonist_ref_count": int(group["expected_protagonist_ref_count"]),
                    "actual_protagonist_ref_count": None,
                    "actual_protagonist_ref_paths": [],
                    "scene_json_path": str(json_path),
                    "state_snapshot_path": str(state_path),
                    "build_context_path": str(build_context_path),
                    "selected_option": selected_option,
                    "next_option_for_followup": next_option,
                    "scene_preview": scene_text,
                    "original_scene_preview": original_scene_text,
                    **hard_meta,
                    "status": "planned",
                }
            )

        merge_flow_update(global_state, option_data)
        global_state.pop("_visual_context", None)
        parent_scene_id = f"{game_id}_seg{segment_index}"
        if next_option:
            selected_option = next_option

    game_summary = {
        "dataset_id": dataset_id,
        "dataset_variant": dataset_variant,
        "theme_id": theme_id,
        "theme": theme_text,
        "style_label_zh": style_label,
        "base_game_id": game_id,
        "segment_count": segment_count,
        "dataset_game_dir": str(game_dir),
        "build_context_path": str(build_context_path),
        "generated_at_utc": utc_now().isoformat(),
    }
    return dataset_rows, game_summary, segment_rows


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    settings = resolve_size_settings(
        config,
        args.size,
        overrides={
            "seed": args.seed if args.seed is not None else None,
            "max_themes": args.max_themes,
            "segments_per_game": args.segments_per_game,
        },
    )
    group_specs = get_group_specs(config)
    theme_catalog = load_theme_items(args.themes_json)
    selected_theme_items = select_theme_items(theme_catalog, settings, args.theme_ids)
    if not selected_theme_items:
        raise SystemExit("No themes selected for dataset build.")

    variant_output_dir = args.output_dir if args.dataset_variant == "general" else args.output_dir / args.dataset_variant
    dataset_id_prefix = "protagonist_ref_dataset" if args.dataset_variant == "general" else f"protagonist_ref_{args.dataset_variant}_dataset"
    dataset_id = args.dataset_name.strip() or f"{dataset_id_prefix}_{utc_timestamp()}"
    dataset_dir = variant_output_dir / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    dataset_rows: List[Dict[str, Any]] = []
    game_rows: List[Dict[str, Any]] = []
    segment_rows: List[Dict[str, Any]] = []

    for theme_item in selected_theme_items:
        rows, game_summary, segments = build_segment_rows(
            dataset_id=dataset_id,
            dataset_variant=args.dataset_variant,
            dataset_dir=dataset_dir,
            theme_item=theme_item,
            settings=settings,
            group_specs=group_specs,
        )
        dataset_rows.extend(rows)
        game_rows.append(game_summary)
        segment_rows.extend(segments)

    config_snapshot = {
        "dataset_id": dataset_id,
        "dataset_variant": args.dataset_variant,
        "generated_at_utc": utc_now().isoformat(),
        "size": settings["size"],
        "seed": settings["seed"],
        "max_themes": settings["max_themes"],
        "segments_per_game": settings["segments_per_game"],
        "selected_theme_ids": [int(item["id"]) for item in selected_theme_items],
        "selected_theme_names": [item.get("theme") for item in selected_theme_items],
        "group_specs": group_specs,
        "config_path": str(args.config),
    }

    dataset_manifest_json = dataset_dir / "dataset_manifest.json"
    dataset_manifest_jsonl = dataset_dir / "dataset_manifest.jsonl"
    dataset_manifest_xlsx = dataset_dir / "dataset_manifest.xlsx"
    game_index_json = dataset_dir / "dataset_games.json"
    segment_index_jsonl = dataset_dir / "dataset_segments.jsonl"
    snapshot_json = dataset_dir / "config_snapshot.json"

    write_json(
        dataset_manifest_json,
        {
            "dataset_id": dataset_id,
            "generated_at_utc": utc_now().isoformat(),
            "settings": settings,
            "group_specs": group_specs,
            "rows": dataset_rows,
        },
    )
    write_jsonl(dataset_manifest_jsonl, dataset_rows)
    write_json(game_index_json, game_rows)
    write_jsonl(segment_index_jsonl, segment_rows)
    write_json(snapshot_json, config_snapshot)
    write_workbook(
        dataset_manifest_xlsx,
        {
            "dataset_manifest": dataset_rows,
            "dataset_games": game_rows,
            "dataset_segments": segment_rows,
            "config_snapshot": flatten_dict(config_snapshot),
        },
    )

    latest_prefix = "latest" if args.dataset_variant == "general" else f"latest_{args.dataset_variant}"
    copy_latest(dataset_manifest_json, variant_output_dir / f"{latest_prefix}_dataset_manifest.json")
    copy_latest(dataset_manifest_jsonl, variant_output_dir / f"{latest_prefix}_dataset_manifest.jsonl")
    copy_latest(dataset_manifest_xlsx, variant_output_dir / f"{latest_prefix}_dataset_manifest.xlsx")

    summary = {
        "dataset_id": dataset_id,
        "dataset_variant": args.dataset_variant,
        "dataset_dir": str(dataset_dir),
        "game_count": len(game_rows),
        "segment_count": len(segment_rows),
        "group_row_count": len(dataset_rows),
        "group_count": len(group_specs),
        "dataset_manifest_json": str(dataset_manifest_json),
        "dataset_manifest_jsonl": str(dataset_manifest_jsonl),
        "dataset_manifest_xlsx": str(dataset_manifest_xlsx),
    }
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

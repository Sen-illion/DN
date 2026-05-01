from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

THIS_DIR = Path(__file__).resolve().parent
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

from src.image.api_providers import generate_scene_image

from common import (
    DEFAULT_OUTPUT_ROOT,
    as_text,
    discover_source_games,
    load_config,
    load_json,
    now_utc_iso,
    write_json,
)
from run_generation_context_ablation import (
    build_global_state,
    generation_output_paths,
    materialize_image,
)


def parse_theme_ids(raw: str) -> list[int]:
    return [int(part.strip()) for part in (raw or "").split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume missing paper baseline images without scoring.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--theme-ids", type=str, default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    manifest = load_json(args.dataset_manifest)
    wanted_theme_ids = set(parse_theme_ids(args.theme_ids))
    games = {game.game_id: game for game in discover_source_games()}
    groups: Dict[str, Dict[str, Any]] = config.get("groups", {})
    runtime: Dict[str, Any] = config.get("runtime", {})
    run_dir = args.output_root / "runs" / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks = manifest.get("tasks", [])
    planned = []
    for task in tasks:
        if wanted_theme_ids and int(task.get("theme_id", -1)) not in wanted_theme_ids:
            continue
        if int(task.get("segment_index", 0)) != 2:
            continue
        planned.append(task)

    rows = []
    for task in planned:
        group = as_text(task.get("group")).strip()
        source_game_id = as_text(task.get("game_id")).strip()
        source_game = games.get(source_game_id)
        if not source_game or group not in groups:
            continue
        group_cfg = groups[group]
        run_game_id = f"{source_game_id}__{group}__{args.run_name}"
        generated_by_segment: Dict[int, Path] = {}

        for segment_index in (1, 2):
            source_segment = source_game.segments.get(segment_index)
            if source_segment is None:
                continue
            task_type = "warmup" if segment_index == 1 else "eval"
            effective_group = group
            effective_group_cfg = dict(group_cfg)
            previous_image_path: Optional[Path] = None
            previous_prompt = ""
            previous_scene_text = ""
            if segment_index == 1:
                effective_group = f"{group}_warmup_seed"
                effective_group_cfg["prompt_strategy"] = "provided"
                effective_group_cfg["use_previous_image"] = False
            elif bool(group_cfg.get("use_previous_image")):
                previous_image_path = generated_by_segment.get(1)
                if previous_image_path is None:
                    previous = source_game.segments.get(1)
                    previous_image_path = previous.image_path if previous else None
                    previous_prompt = previous.prompt if previous else ""
                    previous_scene_text = previous.scene if previous else ""
                else:
                    previous = source_game.segments.get(1)
                    previous_prompt = previous.prompt if previous else ""
                    previous_scene_text = previous.scene if previous else ""

            dest_image_path, dest_json_path = generation_output_paths(run_dir, group, source_game_id, segment_index)
            if dest_image_path.is_file() and dest_json_path.is_file():
                generated_by_segment[segment_index] = dest_image_path.resolve()
                rows.append({"group": group, "game_id": source_game_id, "segment_index": segment_index, "status": "skipped_existing"})
                continue

            global_state = build_global_state(
                run_game_id=run_game_id,
                theme=source_game.theme,
                image_style=source_game.image_style,
                scene_text=source_segment.scene,
                prompt_text=source_segment.prompt,
                prompt_json=source_segment.prompt_json,
                source_first_prompt=(source_game.segments.get(1).prompt if source_game.segments.get(1) else ""),
                group_name=effective_group,
                group_cfg=effective_group_cfg,
                runtime_cfg=runtime,
                previous_image_path=previous_image_path,
                previous_prompt=previous_prompt,
                previous_scene_text=previous_scene_text,
            )
            started = time.perf_counter()
            try:
                result = generate_scene_image(
                    source_segment.scene,
                    global_state,
                    runtime.get("default_style", "default"),
                    use_cache=bool(runtime.get("use_cache", True)),
                    cache_key_suffix=f"{args.run_name}_{group}_{source_game_id}_{segment_index:03d}",
                    skip_cache_lookup=bool(runtime.get("skip_cache_lookup", True)),
                ) or {}
                generated = materialize_image(result, dest_image_path)
                if generated is None:
                    raise RuntimeError("provider returned no materialized image")
                payload = {
                    "group": group,
                    "source_game_id": source_game_id,
                    "run_game_id": run_game_id,
                    "theme_id": source_game.theme_id,
                    "theme": source_game.theme,
                    "segment_index": segment_index,
                    "task_type": task_type,
                    "source_scene": source_segment.scene,
                    "source_prompt": source_segment.prompt,
                    "image_result": result,
                    "generated_image_path": str(generated),
                    "used_prompt_json": global_state.get("_last_scene_prompt_json"),
                    "generated_at_utc": now_utc_iso(),
                }
                write_json(dest_json_path, payload)
                generated_by_segment[segment_index] = generated
                rows.append(
                    {
                        "group": group,
                        "game_id": source_game_id,
                        "segment_index": segment_index,
                        "status": "generated",
                        "elapsed_seconds": round(time.perf_counter() - started, 3),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                rows.append({"group": group, "game_id": source_game_id, "segment_index": segment_index, "status": "failed", "error": str(exc)})

    write_json(run_dir / "resume_generation_summary.json", rows)
    print(run_dir)
    return 0 if not any(row.get("status") == "failed" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

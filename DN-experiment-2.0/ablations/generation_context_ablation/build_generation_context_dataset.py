from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SOURCE_EXPERIMENT_ROOT,
    DEFAULT_THEMES_PATH,
    build_dataset_manifest,
    load_config,
    write_dataset_artifacts,
)


def parse_theme_ids(raw: str) -> list[int]:
    values: list[int] = []
    for part in (raw or "").split(","):
        text = part.strip()
        if not text:
            continue
        values.append(int(text))
    return sorted(set(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the generation-context ablation dataset manifest.")
    parser.add_argument("--scale", type=str, default="pilot", help="Dataset scale preset: pilot / standard / full.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for source-game selection.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to the ablation config JSON.")
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
        help="Root directory for dataset artifacts.",
    )
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


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
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
    outputs = write_dataset_artifacts(dataset_manifest, output_root=args.output_root)
    print(f"dataset_manifest_json={outputs['dataset_manifest_json']}")
    print(f"dataset_manifest_jsonl={outputs['dataset_manifest_jsonl']}")
    print(f"dataset_manifest_xlsx={outputs['dataset_manifest_xlsx']}")
    for group_name, group_outputs in (outputs.get("group_manifests") or {}).items():
        print(f"group_{group_name}_json={group_outputs['json']}")
        print(f"group_{group_name}_jsonl={group_outputs['jsonl']}")
        print(f"group_{group_name}_xlsx={group_outputs['xlsx']}")

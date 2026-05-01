from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    ABLATION_ROOT,
    DEFAULT_CONFIG_PATH,
    DEFAULT_RESULTS_ROOT,
    DEFAULT_SOURCE_ROOT,
    DEFAULT_THEMES_FILE,
    DatasetBuildResult,
    GROUP_SPECS,
    build_dataset_id,
    ensure_dir,
    flatten_mapping,
    list_segment_jsons,
    load_json,
    load_module,
    load_theme_items,
    resolve_path_from_repo,
    resolve_scale_config,
    select_theme_items,
    utc_timestamp,
    write_json,
    write_jsonl,
    write_workbook,
)

RUN_TEXT_SEGMENTS_PATH = ABLATION_ROOT.parents[1] / 'run_text_segments_test.py'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build prompt optimizer ablation dataset manifest.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument('--scale', choices=('pilot', 'standard', 'full'), default='pilot')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--themes-file', type=Path, default=DEFAULT_THEMES_FILE)
    parser.add_argument('--dataset-id', type=str, default='')
    parser.add_argument('--theme-ids', type=str, default='')
    parser.add_argument('--source-root', type=Path, default=None, help='Reuse existing theme_* folders instead of generating text-only source data.')
    parser.add_argument('--output-root', type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument('--force', action='store_true')
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, Any]:
    if path.is_file():
        return dict(load_json(path) or {})
    return {}


def parse_theme_ids(csv_value: str) -> List[int]:
    out: List[int] = []
    for part in (csv_value or '').split(','):
        token = part.strip()
        if token.isdigit():
            out.append(int(token))
    return out


def theme_folder_name(theme_id: int) -> str:
    return f'theme_{theme_id:03d}_'


def find_existing_theme_folder(source_root: Path, theme_id: int) -> Optional[Path]:
    prefix = theme_folder_name(theme_id)
    matches = [path for path in sorted(source_root.glob(f'{prefix}*')) if path.is_dir() and list_segment_jsons(path)]
    return matches[0] if matches else None


def generate_source_dataset(
    *,
    selected_items: List[Dict[str, Any]],
    source_root: Path,
    segments_per_theme: int,
    worldview_constraint: str,
    prev_scene_feedback: str,
) -> None:
    module = load_module('prompt_optimizer_run_text_segments', RUN_TEXT_SEGMENTS_PATH)
    for item in selected_items:
        module.run_one_theme_n_segments(
            item,
            segments_per_theme,
            text_only=True,
            output_root=source_root,
            worldview_constraint=worldview_constraint,
            prev_scene_feedback=prev_scene_feedback,
        )


def build_manifest_rows(
    *,
    selected_items: List[Dict[str, Any]],
    source_root: Path,
    dataset_id: str,
    segments_per_theme: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in selected_items:
        theme_id = int(item['id'])
        folder = find_existing_theme_folder(source_root, theme_id)
        if folder is None:
            raise FileNotFoundError(f'Missing source folder for theme_id={theme_id}: {source_root}')
        json_files = list_segment_jsons(folder)[: max(1, segments_per_theme)]
        manifest_payload: Dict[str, Any] = {}
        manifest_path: Optional[Path] = None
        for json_path in json_files:
            payload = dict(load_json(json_path) or {})
            game_id = str(payload.get('game_id') or '').strip()
            if manifest_path is None and game_id:
                candidate = folder / f'{game_id}_manifest.json'
                if candidate.is_file():
                    manifest_path = candidate
                    try:
                        manifest_payload = dict(load_json(candidate) or {})
                    except Exception:
                        manifest_payload = {}
            segment_index = int(payload.get('segment_index') or 0)
            scene_text = str(payload.get('scene') or '').strip()
            option_text = str(payload.get('option') or '').strip()
            for group in GROUP_SPECS:
                rows.append(
                    {
                        'dataset_id': dataset_id,
                        'theme_id': theme_id,
                        'theme': str(item.get('theme') or ''),
                        'style_label_zh': str(item.get('style_label_zh') or ''),
                        'image_style': json.dumps(item.get('image_style') or {}, ensure_ascii=False),
                        'game_id': game_id,
                        'segment_index': segment_index,
                        'optimizer_group': group['optimizer_group'],
                        'optimizer_enabled': group['optimizer_enabled'],
                        'source_scene_text': scene_text,
                        'source_option_text': option_text,
                        'raw_prompt': scene_text,
                        'final_image_prompt': '',
                        'was_optimized': group['optimizer_enabled'],
                        'source_folder': folder.resolve().as_posix(),
                        'source_json': json_path.resolve().as_posix(),
                        'source_manifest_json': manifest_path.resolve().as_posix() if manifest_path and manifest_path.is_file() else '',
                        'source_segment_json': json_path.name,
                        'dataset_generated_at_utc': utc_timestamp(),
                    }
                )
    rows.sort(key=lambda row: (row['theme_id'], row['game_id'], row['segment_index'], row['optimizer_group']))
    return rows


def build_dataset(
    *,
    config: Dict[str, Any],
    scale: str,
    seed: Optional[int],
    themes_file: Path,
    dataset_id: str,
    theme_ids: Optional[List[int]],
    source_root: Optional[Path],
    output_root: Path,
    force: bool,
) -> DatasetBuildResult:
    dataset_cfg = dict(config.get('dataset') or {})
    seed_value = int(seed if seed is not None else dataset_cfg.get('seed') or 20260425)
    scale_cfg = resolve_scale_config(config, scale)
    theme_items = load_theme_items(themes_file)
    selected_items = select_theme_items(
        theme_items,
        theme_count=scale_cfg['theme_count'],
        seed=seed_value,
        explicit_theme_ids=theme_ids,
    )
    if not selected_items:
        raise RuntimeError('No theme items selected for dataset build.')

    if not dataset_id:
        dataset_id = build_dataset_id(
            scale,
            seed_value,
            len(selected_items),
            scale_cfg['segments_per_theme'],
            suffix='prompt_optimizer',
        )

    dataset_dir = ensure_dir(output_root / dataset_id)
    source_dataset_root = ensure_dir(dataset_dir / 'source_text_dataset')

    if source_root is not None:
        resolved_source_root = source_root.resolve()
    else:
        resolved_source_root = source_dataset_root.resolve()
        worldview_constraint = str((dataset_cfg.get('text_generation') or {}).get('worldview_constraint') or 'on')
        prev_scene_feedback = str((dataset_cfg.get('text_generation') or {}).get('prev_scene_feedback') or 'on')
        if force and resolved_source_root.exists():
            pass
        generate_source_dataset(
            selected_items=selected_items,
            source_root=resolved_source_root,
            segments_per_theme=scale_cfg['segments_per_theme'],
            worldview_constraint=worldview_constraint,
            prev_scene_feedback=prev_scene_feedback,
        )

    rows = build_manifest_rows(
        selected_items=selected_items,
        source_root=resolved_source_root,
        dataset_id=dataset_id,
        segments_per_theme=scale_cfg['segments_per_theme'],
    )

    summary = {
        'dataset_id': dataset_id,
        'scale': scale,
        'seed': seed_value,
        'themes_file': themes_file.resolve().as_posix(),
        'theme_count': len(selected_items),
        'segments_per_theme': scale_cfg['segments_per_theme'],
        'manifest_row_count': len(rows),
        'source_root': resolved_source_root.as_posix(),
        'dataset_dir': dataset_dir.resolve().as_posix(),
        'optimizer_groups': [group['optimizer_group'] for group in GROUP_SPECS],
        'selected_theme_ids': [int(item['id']) for item in selected_items],
    }

    manifest_json = dataset_dir / 'dataset_manifest.json'
    manifest_jsonl = dataset_dir / 'dataset_manifest.jsonl'
    manifest_xlsx = dataset_dir / 'dataset_manifest.xlsx'
    summary_json = dataset_dir / 'dataset_summary.json'
    config_snapshot_json = dataset_dir / 'config_snapshot.json'

    payload = {'summary': summary, 'rows': rows}
    write_json(manifest_json, payload)
    write_jsonl(manifest_jsonl, rows)
    write_json(summary_json, summary)
    write_json(config_snapshot_json, config)
    write_workbook(
        manifest_xlsx,
        {
            'dataset_manifest': rows,
            'config_snapshot': flatten_mapping(config or {}),
        },
    )

    return DatasetBuildResult(
        dataset_id=dataset_id,
        dataset_dir=dataset_dir,
        manifest_json=manifest_json,
        manifest_jsonl=manifest_jsonl,
        manifest_xlsx=manifest_xlsx,
        summary_json=summary_json,
    )


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    theme_ids = parse_theme_ids(args.theme_ids)
    result = build_dataset(
        config=config,
        scale=args.scale,
        seed=args.seed,
        themes_file=args.themes_file.resolve(),
        dataset_id=args.dataset_id.strip(),
        theme_ids=theme_ids or None,
        source_root=args.source_root,
        output_root=args.output_root.resolve(),
        force=args.force,
    )
    print(
        json.dumps(
            {
                'dataset_id': result.dataset_id,
                'dataset_dir': result.dataset_dir.resolve().as_posix(),
                'manifest_json': result.manifest_json.resolve().as_posix(),
                'manifest_jsonl': result.manifest_jsonl.resolve().as_posix(),
                'manifest_xlsx': result.manifest_xlsx.resolve().as_posix(),
                'summary_json': result.summary_json.resolve().as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (
    ABLATION_ROOT,
    DEFAULT_CONFIG_PATH,
    DEFAULT_RESULTS_ROOT,
    DEFAULT_RUNS_ROOT,
    DEFAULT_THEMES_FILE,
    flatten_mapping,
    ensure_dir,
    load_json,
    load_module,
    resolve_path_from_repo,
    theme_index_by_id,
    utc_timestamp,
    write_json,
    write_jsonl,
    write_workbook,
)
from build_prompt_optimizer_dataset import build_dataset

REPO_ROOT = ABLATION_ROOT.parents[2]
EXPORT_IMAGE_PATHS_PATH = REPO_ROOT / 'DN-experiment-2.0' / 'export_image_paths_manifest.py'
EXPERIMENT_SAVE_PATH = REPO_ROOT / 'DN-experiment' / 'experiment_save.py'
SCORE_SCRIPT_PATH = REPO_ROOT / 'DN-experiment-2.0' / '图片一致性_experiment' / 'multiview_image_consistency' / 'scripts' / 'score_image_consistency_per_game.py'

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.image.api_providers import generate_scene_image

DIMENSIONS = [
    'semantic_consistency',
    'subject_attribute_consistency',
    'spatial_consistency',
    'style_lighting_consistency',
    'detail_integrity',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run prompt optimizer ablation and export workbook.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument('--dataset-manifest', type=Path, default=None)
    parser.add_argument('--build-dataset', action='store_true')
    parser.add_argument('--scale', choices=('pilot', 'standard', 'full'), default='pilot')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--theme-ids', type=str, default='')
    parser.add_argument('--themes-file', type=Path, default=DEFAULT_THEMES_FILE)
    parser.add_argument('--source-root', type=Path, default=None)
    parser.add_argument('--run-id', type=str, default='')
    parser.add_argument('--results-root', type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument('--score-existing-run', action='store_true')
    parser.add_argument('--skip-image-generation', action='store_true')
    parser.add_argument('--skip-scoring', action='store_true')
    parser.add_argument('--dry-run-scoring', action='store_true')
    parser.add_argument('--judge-models', type=str, default='')
    parser.add_argument('--max-samples-per-group', type=int, default=0)
    parser.add_argument('--no-xlsx', action='store_true', help='Skip writing Excel workbook (avoids openpyxl dependency).')
    return parser.parse_args()


def parse_theme_ids(csv_value: str) -> List[int]:
    theme_ids: List[int] = []
    for part in (csv_value or '').split(','):
        token = part.strip()
        if token.isdigit():
            theme_ids.append(int(token))
    return theme_ids


def load_config(path: Path) -> Dict[str, Any]:
    if path.is_file():
        return dict(load_json(path) or {})
    return {}


def load_manifest_rows(manifest_path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    payload = dict(load_json(manifest_path) or {})
    summary = dict(payload.get('summary') or {})
    rows = [dict(row) for row in payload.get('rows') or []]
    rows.sort(key=lambda row: (row.get('optimizer_group', ''), row.get('theme_id', 0), row.get('game_id', ''), row.get('segment_index', 0)))
    return summary, rows


def _load_artifact_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    payload = dict(load_json(path) or {})
    return [dict(row) for row in payload.get('rows') or []]


def _rebuild_existing_run_artifacts(
    run_dir: Path,
    manifest_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    generation_rows: List[Dict[str, Any]] = []
    prompt_rows: List[Dict[str, Any]] = []
    resolved_manifest_rows: List[Dict[str, Any]] = []

    for base_row in manifest_rows:
        group = str(base_row.get('optimizer_group') or '')
        theme_id = int(base_row.get('theme_id') or 0)
        game_id = str(base_row.get('game_id') or '')
        segment_index = int(base_row.get('segment_index') or 0)
        group_root = run_dir / 'generated' / group
        folder_matches = [
            path for path in sorted(group_root.glob(f'theme_{theme_id:03d}_{game_id}*'))
            if path.is_dir()
        ]
        json_path = folder_matches[0] / f'{game_id}_{segment_index:03d}.json' if folder_matches else None
        saved_payload = dict(load_json(json_path) or {}) if json_path and json_path.is_file() else {}
        image_file = str(saved_payload.get('image_file') or '').strip()
        image_path = (json_path.parent / image_file).resolve().as_posix() if json_path and image_file and (json_path.parent / image_file).is_file() else ''
        final_prompt = str(saved_payload.get('prompt') or '').strip()
        trace = {
            'raw_prompt': str(base_row.get('source_scene_text') or '').strip(),
            'final_prompt': final_prompt,
            'prompt_optimizer_enabled': bool(base_row.get('optimizer_enabled')),
            'prompt_source': 'optimize_image_prompt_with_llm' if bool(base_row.get('optimizer_enabled')) else 'base_scene_description',
        }
        generation_row = {
            'dataset_id': base_row.get('dataset_id'),
            'optimizer_group': group,
            'optimizer_enabled': base_row.get('optimizer_enabled'),
            'theme_id': theme_id,
            'theme': base_row.get('theme'),
            'game_id': game_id,
            'segment_index': segment_index,
            'generation_success': bool(json_path and json_path.is_file()),
            'generation_duration_sec': None,
            'cached': False,
            'image_path': image_path,
            'image_url': str(saved_payload.get('image_url') or '').strip(),
            'output_json_path': json_path.resolve().as_posix() if json_path and json_path.is_file() else '',
            'error': '' if json_path and json_path.is_file() else 'missing_generated_output',
            'prompt_source': trace['prompt_source'],
            'final_image_prompt': final_prompt,
        }
        generation_rows.append(generation_row)
        prompt_rows.append(prompt_trace_row(base_row, trace, generation_row))

        resolved = dict(base_row)
        resolved['final_image_prompt'] = final_prompt
        resolved['was_optimized'] = bool(base_row.get('optimizer_enabled'))
        resolved['prompt_source'] = trace['prompt_source']
        resolved['generation_success'] = generation_row['generation_success']
        resolved['image_path'] = image_path
        resolved['output_json_path'] = generation_row['output_json_path']
        resolved['generation_error'] = generation_row['error']
        resolved_manifest_rows.append(resolved)

    return generation_rows, prompt_rows, resolved_manifest_rows


def load_existing_run_artifacts(
    run_dir: Path,
    manifest_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    artifacts_dir = run_dir / 'artifacts'
    generation_rows = _load_artifact_rows(artifacts_dir / 'generation_runs.json')
    prompt_rows = _load_artifact_rows(artifacts_dir / 'prompt_trace.json')
    resolved_manifest_rows = _load_artifact_rows(artifacts_dir / 'dataset_manifest_resolved.json')
    if not resolved_manifest_rows:
        generation_rows, prompt_rows, resolved_manifest_rows = _rebuild_existing_run_artifacts(run_dir, manifest_rows)
    return generation_rows, prompt_rows, resolved_manifest_rows


def build_image_path_manifests(output_root: Path) -> None:
    module = load_module('prompt_optimizer_export_image_paths', EXPORT_IMAGE_PATHS_PATH)
    for folder in sorted(path for path in output_root.glob('theme_*') if path.is_dir()):
        manifest = module.build_manifest_for_folder(REPO_ROOT, folder)
        if not manifest:
            continue
        game_id = str(manifest.get('game_id') or folder.name)
        out_path = folder / f'{game_id}_image_paths.json'
        out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


def prompt_trace_row(base_row: Mapping[str, Any], trace: Mapping[str, Any], generation_row: Mapping[str, Any]) -> Dict[str, Any]:
    raw_prompt = str(trace.get('raw_prompt') or base_row.get('source_scene_text') or '').strip()
    final_prompt = str(trace.get('final_prompt') or '').strip()
    return {
        'optimizer_group': base_row.get('optimizer_group'),
        'optimizer_enabled': base_row.get('optimizer_enabled'),
        'theme_id': base_row.get('theme_id'),
        'theme': base_row.get('theme'),
        'game_id': base_row.get('game_id'),
        'segment_index': base_row.get('segment_index'),
        'raw_prompt': raw_prompt,
        'final_prompt': final_prompt,
        'prompt_source': trace.get('prompt_source', ''),
        'was_optimized': bool(trace.get('prompt_optimizer_enabled')),
        'raw_prompt_length': len(raw_prompt),
        'final_prompt_length': len(final_prompt),
        'generation_success': generation_row.get('generation_success', False),
        'image_path': generation_row.get('image_path', ''),
    }


def generation_context_row(base_row: Mapping[str, Any], generation_row: Mapping[str, Any], trace: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'dataset_id': base_row.get('dataset_id'),
        'optimizer_group': base_row.get('optimizer_group'),
        'optimizer_enabled': base_row.get('optimizer_enabled'),
        'theme_id': base_row.get('theme_id'),
        'theme': base_row.get('theme'),
        'game_id': base_row.get('game_id'),
        'segment_index': base_row.get('segment_index'),
        'generation_success': generation_row.get('generation_success', False),
        'generation_duration_sec': generation_row.get('generation_duration_sec'),
        'cached': generation_row.get('cached', False),
        'image_path': generation_row.get('image_path', ''),
        'image_url': generation_row.get('image_url', ''),
        'output_json_path': generation_row.get('output_json_path', ''),
        'error': generation_row.get('error', ''),
        'prompt_source': trace.get('prompt_source', ''),
        'final_image_prompt': trace.get('final_prompt', ''),
    }


def run_generation(
    *,
    manifest_rows: List[Dict[str, Any]],
    run_dir: Path,
    config: Dict[str, Any],
    themes_index: Dict[int, Dict[str, Any]],
    skip_image_generation: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    save_module = load_module('prompt_optimizer_experiment_save', EXPERIMENT_SAVE_PATH)
    generation_cfg = dict(config.get('generation') or {})
    use_cache = bool(generation_cfg.get('use_cache', True))
    skip_cache_lookup = bool(generation_cfg.get('skip_cache_lookup', False))
    chain_previous_image = bool(generation_cfg.get('chain_previous_image', True))
    skip_protagonist_reference = bool(generation_cfg.get('skip_protagonist_reference', True))

    generation_rows: List[Dict[str, Any]] = []
    prompt_rows: List[Dict[str, Any]] = []
    resolved_manifest_rows: List[Dict[str, Any]] = []
    per_group_prev: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for base_row in manifest_rows:
        group = str(base_row.get('optimizer_group') or '')
        group_root = ensure_dir(run_dir / 'generated' / group)
        source_json = Path(str(base_row.get('source_json') or ''))
        source_payload = dict(load_json(source_json) or {})
        theme_id = int(base_row.get('theme_id') or 0)
        theme_item = themes_index.get(theme_id, {})
        scene_text = str(base_row.get('source_scene_text') or source_payload.get('scene') or '').strip()
        game_id = str(base_row.get('game_id') or source_payload.get('game_id') or '').strip()
        segment_index = int(base_row.get('segment_index') or source_payload.get('segment_index') or 0)

        global_state: Dict[str, Any] = {
            'game_id': game_id,
            'tone': 'normal_ending',
            'core_worldview': {},
            'flow_worldline': {},
            '_skip_protagonist_reference': skip_protagonist_reference,
            '_experiment_prompt_optimizer': 'on' if bool(base_row.get('optimizer_enabled')) else 'off',
        }
        if isinstance(theme_item.get('image_style'), dict):
            global_state['image_style'] = theme_item['image_style']
        prev_key = (group, game_id)
        if chain_previous_image and prev_key in per_group_prev:
            prev = per_group_prev[prev_key]
            global_state['_visual_context'] = {
                'sceneId': prev.get('scene_id', f'{game_id}_seg{max(0, segment_index - 1)}'),
                'previousSceneImage': prev.get('scene_image', {}),
                'previousSceneText': prev.get('scene_text', ''),
            }

        generation_error = ''
        image_path = ''
        output_json_path = ''
        image_url = ''
        cached = False
        trace: Dict[str, Any] = {}
        started = time.perf_counter()
        scene_image: Optional[Dict[str, Any]] = None

        try:
            if not skip_image_generation:
                scene_image = generate_scene_image(
                    scene_text,
                    global_state,
                    'default',
                    use_cache=use_cache,
                    cache_key_suffix=f'{group}_{game_id}_seg{segment_index:03d}',
                    skip_cache_lookup=skip_cache_lookup,
                )
            trace = dict(global_state.get('_last_scene_prompt_trace') or {})
            if skip_image_generation:
                generation_error = 'image_generation_skipped'
            elif scene_image and isinstance(scene_image, dict) and scene_image.get('url'):
                prompt_json = global_state.get('_last_scene_prompt_json') if isinstance(global_state.get('_last_scene_prompt_json'), dict) else None
                cached = bool(scene_image.get('cached', False))
                image_url = str(scene_image.get('url') or '').strip()
                scene_payload = {
                    'url': image_url,
                    'prompt': str(scene_image.get('prompt') or '').strip(),
                    'style': scene_image.get('style', 'default'),
                    'width': scene_image.get('width', 0),
                    'height': scene_image.get('height', 0),
                    'cached': cached,
                    'image_type': 'story_scene',
                }
                if prompt_json is not None:
                    scene_payload['prompt_json'] = prompt_json
                option_data = {
                    'scene': scene_text,
                    'sceneId': source_payload.get('scene_id') or f'{game_id}_seg{segment_index:03d}',
                    'scene_image': scene_payload,
                }
                json_path, img_path = save_module.save_segment_to_folder(
                    REPO_ROOT,
                    game_id,
                    segment_index,
                    option_data,
                    global_state,
                    theme_item_id=theme_id,
                    option_text=str(source_payload.get('option') or ''),
                    parent_scene_id=source_payload.get('parent_scene_id') or 'initial',
                    option_index=int(source_payload.get('option_id') or 0),
                    output_root=group_root,
                )
                output_json_path = json_path.resolve().as_posix()
                image_path = img_path.resolve().as_posix() if img_path else ''
                per_group_prev[prev_key] = {
                    'scene_id': option_data['sceneId'],
                    'scene_text': scene_text,
                    'scene_image': scene_payload,
                }
            else:
                generation_error = 'image_generation_returned_empty'
        except Exception as exc:
            trace = dict(global_state.get('_last_scene_prompt_trace') or {})
            generation_error = str(exc)

        duration = round(time.perf_counter() - started, 4)
        generation_row = {
            'dataset_id': base_row.get('dataset_id'),
            'optimizer_group': group,
            'optimizer_enabled': base_row.get('optimizer_enabled'),
            'theme_id': theme_id,
            'theme': base_row.get('theme'),
            'game_id': game_id,
            'segment_index': segment_index,
            'generation_success': bool(output_json_path),
            'generation_duration_sec': duration,
            'cached': cached,
            'image_path': image_path,
            'image_url': image_url,
            'output_json_path': output_json_path,
            'error': generation_error,
        }
        generation_rows.append(generation_context_row(base_row, generation_row, trace))
        prompt_rows.append(prompt_trace_row(base_row, trace, generation_row))

        resolved = dict(base_row)
        resolved['final_image_prompt'] = str(trace.get('final_prompt') or '')
        resolved['was_optimized'] = bool(trace.get('prompt_optimizer_enabled', base_row.get('optimizer_enabled')))
        resolved['prompt_source'] = str(trace.get('prompt_source') or '')
        resolved['generation_success'] = bool(output_json_path)
        resolved['image_path'] = image_path
        resolved['output_json_path'] = output_json_path
        resolved['generation_error'] = generation_error
        resolved_manifest_rows.append(resolved)

    for group in sorted({row['optimizer_group'] for row in manifest_rows}):
        build_image_path_manifests(run_dir / 'generated' / group)

    return generation_rows, prompt_rows, resolved_manifest_rows


def run_scoring_for_group(
    *,
    group_root: Path,
    group_name: str,
    judge_models: str,
    dry_run: bool,
    max_samples: int,
) -> List[Dict[str, Any]]:
    score_module = load_module(f'prompt_optimizer_score_{group_name}', SCORE_SCRIPT_PATH)
    score_module.load_env()
    samples = score_module.build_samples(group_root)
    if max_samples > 0:
        samples = samples[:max_samples]
    raw_rows: List[Dict[str, Any]] = []
    if dry_run or not samples:
        for sample in samples:
            raw_rows.append(
                {
                    'optimizer_group': group_name,
                    'game_id': sample.game_id,
                    'theme_item_id': sample.theme_item_id,
                    'segment_index': sample.segment_index,
                    'sample_id': sample.sample_id,
                    'judge_model': 'dry-run',
                    'overall_score': '',
                    'semantic_consistency': '',
                    'subject_attribute_consistency': '',
                    'spatial_consistency': '',
                    'style_lighting_consistency': '',
                    'detail_integrity': '',
                    'confidence': '',
                    'reasons': '',
                    'failure_tags': '',
                    'image_path': str(sample.image_path),
                }
            )
        return raw_rows

    models = score_module.parse_models(judge_models)
    if not models:
        env_models = score_module.parse_models(str((os.getenv('COHERENCE_MODELS') or '').strip()))
        models = env_models
    api_key = score_module.env_str('COHERENCE_API_KEY') or score_module.env_str('VISION_REF_API_KEY') or score_module.env_str('Origin_Segment_Analyst_API_KEY')
    base_url = score_module.env_str('COHERENCE_BASE_URL') or score_module.env_str('VISION_REF_BASE_URL') or score_module.env_str('Origin_Segment_Analyst_BASE_URL') or 'https://api.openai.com/v1'
    if not models or not api_key:
        return run_scoring_for_group(
            group_root=group_root,
            group_name=group_name,
            judge_models=judge_models,
            dry_run=True,
            max_samples=max_samples,
        )

    client = score_module.OpenAI(api_key=api_key, base_url=base_url)
    for sample in samples:
        for model in models:
            result = score_module.score_sample(client, model, sample)
            raw_rows.append(
                {
                    'optimizer_group': group_name,
                    'game_id': sample.game_id,
                    'theme_item_id': sample.theme_item_id,
                    'segment_index': sample.segment_index,
                    'sample_id': sample.sample_id,
                    'judge_model': model,
                    'overall_score': result['overall_score'],
                    'semantic_consistency': result['dimension_scores']['semantic_consistency'],
                    'subject_attribute_consistency': result['dimension_scores']['subject_attribute_consistency'],
                    'spatial_consistency': result['dimension_scores']['spatial_consistency'],
                    'style_lighting_consistency': result['dimension_scores']['style_lighting_consistency'],
                    'detail_integrity': result['dimension_scores']['detail_integrity'],
                    'confidence': result['confidence'],
                    'reasons': ' | '.join(result['reasons']),
                    'failure_tags': ','.join(result['failure_tags']),
                    'image_path': str(sample.image_path),
                }
            )
    return raw_rows


def aggregate_per_sample(score_rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in score_rows:
        sample_id = str(row.get('sample_id') or '')
        group = str(row.get('optimizer_group') or '')
        buckets[(group, sample_id)].append(row)
    rows: List[Dict[str, Any]] = []
    for (group, sample_id), bucket in sorted(buckets.items()):
        numeric = [row for row in bucket if isinstance(row.get('overall_score'), (int, float))]
        base = dict(bucket[0])
        row = {
            'optimizer_group': group,
            'game_id': base.get('game_id'),
            'theme_item_id': base.get('theme_item_id'),
            'segment_index': base.get('segment_index'),
            'sample_id': sample_id,
            'judge_count': len(bucket),
            'valid_judge_count': len(numeric),
            'image_path': base.get('image_path', ''),
        }
        if numeric:
            row['overall_score_mean'] = round(statistics.mean(float(item['overall_score']) for item in numeric), 4)
            row['confidence_mean'] = round(statistics.mean(float(item['confidence']) for item in numeric), 4)
            for dim in DIMENSIONS:
                row[f'{dim}_mean'] = round(statistics.mean(float(item[dim]) for item in numeric), 4)
            row['failure_tags'] = ' | '.join(sorted({str(item.get('failure_tags') or '') for item in numeric if str(item.get('failure_tags') or '').strip()}))
            row['reasons'] = ' | '.join(str(item.get('reasons') or '') for item in numeric if str(item.get('reasons') or '').strip())
        else:
            row['overall_score_mean'] = ''
            row['confidence_mean'] = ''
            for dim in DIMENSIONS:
                row[f'{dim}_mean'] = ''
            row['failure_tags'] = ''
            row['reasons'] = ''
        rows.append(row)
    return rows


def safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(statistics.mean(values), 4)


def summarize_groups(
    *,
    manifest_rows: List[Dict[str, Any]],
    generation_rows: List[Dict[str, Any]],
    prompt_rows: List[Dict[str, Any]],
    per_sample_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    manifest_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    generation_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    prompt_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    sample_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in manifest_rows:
        manifest_by_group[str(row.get('optimizer_group') or '')].append(row)
    for row in generation_rows:
        generation_by_group[str(row.get('optimizer_group') or '')].append(row)
    for row in prompt_rows:
        prompt_by_group[str(row.get('optimizer_group') or '')].append(row)
    for row in per_sample_rows:
        sample_by_group[str(row.get('optimizer_group') or '')].append(row)

    summary_rows: List[Dict[str, Any]] = []
    for group in sorted(manifest_by_group.keys()):
        planned = manifest_by_group[group]
        generated = generation_by_group.get(group, [])
        prompts = prompt_by_group.get(group, [])
        samples = sample_by_group.get(group, [])
        successful_generations = [row for row in generated if row.get('generation_success')]
        valid_samples = [row for row in samples if isinstance(row.get('overall_score_mean'), (int, float))]
        duration_values = [float(row['generation_duration_sec']) for row in successful_generations if isinstance(row.get('generation_duration_sec'), (int, float))]
        prompt_lengths = [int(row['final_prompt_length']) for row in prompts if isinstance(row.get('final_prompt_length'), int) and row['final_prompt_length'] > 0]
        summary = {
            'optimizer_group': group,
            'planned_samples': len(planned),
            'generated_samples': len(successful_generations),
            'valid_samples': len(valid_samples),
            'coverage': round(len(valid_samples) / len(planned), 4) if planned else 0.0,
            'generation_success_rate': round(len(successful_generations) / len(planned), 4) if planned else 0.0,
            'overall_score_mean': safe_mean([float(row['overall_score_mean']) for row in valid_samples if isinstance(row.get('overall_score_mean'), (int, float))]),
            'avg_generation_duration_sec': safe_mean(duration_values),
            'prompt_length_mean': safe_mean([float(value) for value in prompt_lengths]),
            'prompt_length_median': round(statistics.median(prompt_lengths), 4) if prompt_lengths else None,
        }
        for dim in DIMENSIONS:
            values = [float(row[f'{dim}_mean']) for row in valid_samples if isinstance(row.get(f'{dim}_mean'), (int, float))]
            summary[f'{dim}_mean'] = safe_mean(values)
        summary_rows.append(summary)
    return summary_rows


def build_group_comparison(summary_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_group = {str(row.get('optimizer_group') or ''): row for row in summary_rows}
    on_row = by_group.get('prompt_optimizer_on', {})
    off_row = by_group.get('prompt_optimizer_off', {})
    metrics = ['overall_score_mean', 'coverage', 'generation_success_rate', 'avg_generation_duration_sec', 'prompt_length_mean'] + [f'{dim}_mean' for dim in DIMENSIONS]
    rows: List[Dict[str, Any]] = []
    for metric in metrics:
        on_value = on_row.get(metric)
        off_value = off_row.get(metric)
        delta = None
        if isinstance(on_value, (int, float)) and isinstance(off_value, (int, float)):
            delta = round(float(on_value) - float(off_value), 4)
        rows.append(
            {
                'metric': metric,
                'prompt_optimizer_on': on_value,
                'prompt_optimizer_off': off_value,
                'delta_on_minus_off': delta,
            }
        )
    return rows


def build_failure_cases(
    *,
    generation_rows: List[Dict[str, Any]],
    per_sample_rows: List[Dict[str, Any]],
    threshold: float,
) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    for row in generation_rows:
        if not row.get('generation_success'):
            failures.append(
                {
                    'optimizer_group': row.get('optimizer_group'),
                    'game_id': row.get('game_id'),
                    'segment_index': row.get('segment_index'),
                    'failure_type': 'generation_failure',
                    'details': row.get('error', ''),
                }
            )
    for row in per_sample_rows:
        score = row.get('overall_score_mean')
        if isinstance(score, (int, float)) and float(score) < threshold:
            failures.append(
                {
                    'optimizer_group': row.get('optimizer_group'),
                    'game_id': row.get('game_id'),
                    'segment_index': row.get('segment_index'),
                    'failure_type': 'low_consistency_score',
                    'details': f'overall_score_mean={score}',
                    'reasons': row.get('reasons', ''),
                    'failure_tags': row.get('failure_tags', ''),
                }
            )
    return failures


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    theme_ids = parse_theme_ids(args.theme_ids)

    # Map 云雾 env vars to the coherence scorer env slots when present.
    if not (os.getenv('COHERENCE_API_KEY') or '').strip():
        yunwu_key = (os.getenv('YUNWU_API_KEY') or '').strip()
        if yunwu_key:
            os.environ['COHERENCE_API_KEY'] = yunwu_key
    if not (os.getenv('COHERENCE_BASE_URL') or '').strip():
        yunwu_base = (os.getenv('YUNWU_BASE_URL') or '').strip()
        if yunwu_base:
            os.environ['COHERENCE_BASE_URL'] = yunwu_base

    manifest_path = args.dataset_manifest
    if args.build_dataset or manifest_path is None:
        dataset_result = build_dataset(
            config=config,
            scale=args.scale,
            seed=args.seed,
            themes_file=args.themes_file.resolve(),
            dataset_id='',
            theme_ids=theme_ids or None,
            source_root=args.source_root,
            output_root=(DEFAULT_RESULTS_ROOT / 'datasets').resolve(),
            force=False,
        )
        manifest_path = dataset_result.manifest_json

    if manifest_path is None or not manifest_path.is_file():
        raise FileNotFoundError('Dataset manifest was not found.')

    manifest_summary, manifest_rows = load_manifest_rows(manifest_path)
    run_id = args.run_id.strip() or f'run_{utc_timestamp()}'
    run_dir = ensure_dir(args.results_root.resolve() / run_id)
    themes_index = theme_index_by_id(args.themes_file.resolve())
    if args.score_existing_run:
        generation_rows, prompt_rows, resolved_manifest_rows = load_existing_run_artifacts(run_dir, manifest_rows)
    else:
        generation_rows, prompt_rows, resolved_manifest_rows = run_generation(
            manifest_rows=manifest_rows,
            run_dir=run_dir,
            config=config,
            themes_index=themes_index,
            skip_image_generation=args.skip_image_generation,
        )

    score_rows: List[Dict[str, Any]] = []
    can_score = not args.skip_scoring and (args.score_existing_run or not args.skip_image_generation)
    if can_score:
        for group in sorted({row['optimizer_group'] for row in manifest_rows}):
            group_root = run_dir / 'generated' / group
            score_rows.extend(
                run_scoring_for_group(
                    group_root=group_root,
                    group_name=group,
                    judge_models=args.judge_models,
                    dry_run=args.dry_run_scoring,
                    max_samples=max(0, int(args.max_samples_per_group)),
                )
            )

    per_sample_rows = aggregate_per_sample(score_rows)
    threshold = float(((config.get('scoring') or {}).get('failure_score_threshold')) or 3.0)
    group_summary_rows = summarize_groups(
        manifest_rows=resolved_manifest_rows,
        generation_rows=generation_rows,
        prompt_rows=prompt_rows,
        per_sample_rows=per_sample_rows,
    )
    comparison_rows = build_group_comparison(group_summary_rows)
    failure_rows = build_failure_cases(
        generation_rows=generation_rows,
        per_sample_rows=per_sample_rows,
        threshold=threshold,
    )
    config_snapshot = {
        'run_id': run_id,
        'dataset_manifest': manifest_path.resolve().as_posix(),
        'run_dir': run_dir.resolve().as_posix(),
        'build_dataset': args.build_dataset,
        'score_existing_run': args.score_existing_run,
        'scale': args.scale,
        'seed': args.seed,
        'skip_image_generation': args.skip_image_generation,
        'skip_scoring': args.skip_scoring,
        'dry_run_scoring': args.dry_run_scoring,
        'judge_models': args.judge_models,
        'config': config,
        'dataset_summary': manifest_summary,
    }

    artifacts_dir = ensure_dir(run_dir / 'artifacts')
    workbook_path = artifacts_dir / 'prompt_optimizer_ablation_results.xlsx'
    write_json(artifacts_dir / 'dataset_manifest_resolved.json', {'rows': resolved_manifest_rows})
    write_jsonl(artifacts_dir / 'dataset_manifest_resolved.jsonl', resolved_manifest_rows)
    write_json(artifacts_dir / 'generation_runs.json', {'rows': generation_rows})
    write_jsonl(artifacts_dir / 'generation_runs.jsonl', generation_rows)
    write_json(artifacts_dir / 'prompt_trace.json', {'rows': prompt_rows})
    write_jsonl(artifacts_dir / 'prompt_trace.jsonl', prompt_rows)
    write_json(artifacts_dir / 'per_sample_results.json', {'rows': per_sample_rows})
    write_jsonl(artifacts_dir / 'per_sample_results.jsonl', per_sample_rows)
    write_json(artifacts_dir / 'group_summary.json', {'rows': group_summary_rows})
    write_json(artifacts_dir / 'group_comparison.json', {'rows': comparison_rows})
    write_json(artifacts_dir / 'failure_cases.json', {'rows': failure_rows})
    write_jsonl(artifacts_dir / 'failure_cases.jsonl', failure_rows)
    write_json(artifacts_dir / 'config_snapshot.json', config_snapshot)
    if score_rows:
        write_json(artifacts_dir / 'raw_score_rows.json', {'rows': score_rows})
        write_jsonl(artifacts_dir / 'raw_score_rows.jsonl', score_rows)

    if not args.no_xlsx:
        write_workbook(
            workbook_path,
            {
                'dataset_manifest': resolved_manifest_rows,
                'generation_runs': generation_rows,
                'prompt_trace': prompt_rows,
                'per_sample_results': per_sample_rows,
                'group_summary': group_summary_rows,
                'group_comparison': comparison_rows,
                'failure_cases': failure_rows,
                'config_snapshot': flatten_mapping(config_snapshot),
            },
        )

    summary = {
        'run_id': run_id,
        'run_dir': run_dir.resolve().as_posix(),
        'workbook_path': workbook_path.resolve().as_posix() if not args.no_xlsx else '',
        'dataset_manifest': manifest_path.resolve().as_posix(),
        'generated_rows': len(generation_rows),
        'scored_rows': len(score_rows),
        'per_sample_rows': len(per_sample_rows),
    }
    write_json(artifacts_dir / 'run_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

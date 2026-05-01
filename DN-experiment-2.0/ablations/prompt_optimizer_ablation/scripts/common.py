from __future__ import annotations

import importlib.util
import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]
ABLATION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ABLATION_ROOT / 'config' / 'default_config.json'
DEFAULT_RESULTS_ROOT = ABLATION_ROOT / 'results'
DEFAULT_THEMES_FILE = REPO_ROOT / 'game_themes_100.json'
DEFAULT_SOURCE_ROOT = DEFAULT_RESULTS_ROOT / 'datasets'
DEFAULT_RUNS_ROOT = DEFAULT_RESULTS_ROOT / 'runs'

try:
    from openpyxl import Workbook  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Workbook = None  # type: ignore

GROUP_SPECS = [
    {'optimizer_group': 'prompt_optimizer_off', 'optimizer_enabled': False},
    {'optimizer_group': 'prompt_optimizer_on', 'optimizer_enabled': True},
]

DEFAULT_SCALE_PRESETS = {
    'pilot': {'theme_count': 2, 'segments_per_theme': 2},
    'standard': {'theme_count': 6, 'segments_per_theme': 4},
    'full': {'theme_count': 12, 'segments_per_theme': 6},
}


@dataclass
class DatasetBuildResult:
    dataset_id: str
    dataset_dir: Path
    manifest_json: Path
    manifest_jsonl: Path
    manifest_xlsx: Path
    summary_json: Path


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False) + '\n')


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_theme_items(themes_file: Path) -> List[Dict[str, Any]]:
    payload = load_json(themes_file)
    items = payload.get('items') or []
    return [item for item in items if isinstance(item, dict)]


def theme_index_by_id(themes_file: Path) -> Dict[int, Dict[str, Any]]:
    index: Dict[int, Dict[str, Any]] = {}
    for item in load_theme_items(themes_file):
        raw_id = item.get('id')
        if isinstance(raw_id, int):
            index[raw_id] = item
    return index


def resolve_scale_config(config: Mapping[str, Any], scale: str) -> Dict[str, int]:
    dataset_cfg = dict(config.get('dataset') or {})
    preset_cfg = dict(dataset_cfg.get('scale_presets') or DEFAULT_SCALE_PRESETS)
    chosen = dict(preset_cfg.get(scale) or DEFAULT_SCALE_PRESETS.get(scale) or DEFAULT_SCALE_PRESETS['pilot'])
    theme_count = int(dataset_cfg.get('theme_count') or chosen.get('theme_count') or 0)
    segments_per_theme = int(dataset_cfg.get('segments_per_theme') or chosen.get('segments_per_theme') or 0)
    return {
        'theme_count': max(1, theme_count),
        'segments_per_theme': max(1, segments_per_theme),
    }


def select_theme_items(
    theme_items: List[Dict[str, Any]],
    *,
    theme_count: int,
    seed: int,
    explicit_theme_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    if explicit_theme_ids:
        by_id = {int(item['id']): item for item in theme_items if isinstance(item.get('id'), int)}
        selected: List[Dict[str, Any]] = []
        for theme_id in explicit_theme_ids:
            item = by_id.get(int(theme_id))
            if item:
                selected.append(item)
        return selected
    rng = random.Random(seed)
    pool = [item for item in theme_items if isinstance(item.get('id'), int)]
    pool.sort(key=lambda item: int(item['id']))
    rng.shuffle(pool)
    chosen = pool[: max(1, min(theme_count, len(pool)))]
    chosen.sort(key=lambda item: int(item['id']))
    return chosen


def list_segment_jsons(folder: Path) -> List[Path]:
    files = sorted(folder.glob('game_*_[0-9][0-9][0-9].json'))
    return [path for path in files if 'manifest' not in path.name.lower() and 'image_paths' not in path.name.lower()]


def flatten_mapping(mapping: Mapping[str, Any], prefix: str = '') -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key in sorted(mapping.keys()):
        value = mapping[key]
        joined = f'{prefix}.{key}' if prefix else str(key)
        if isinstance(value, Mapping):
            rows.extend(flatten_mapping(value, joined))
        else:
            rows.append({'key': joined, 'value': json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value})
    return rows


def write_workbook(path: Path, sheets: Mapping[str, List[Mapping[str, Any]]]) -> None:
    if Workbook is None:
        raise RuntimeError("openpyxl is not installed; cannot write xlsx. Re-run with --no-xlsx.")
    wb = Workbook()
    first = True
    for sheet_name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet(sheet_name)
        ws.title = sheet_name
        first = False
        normalized_rows = [dict(row) for row in rows]
        headers: List[str] = []
        for row in normalized_rows:
            for key in row.keys():
                if key not in headers:
                    headers.append(key)
        if not headers:
            headers = ['note']
            normalized_rows = [{'note': ''}]
        ws.append(headers)
        for row in normalized_rows:
            ws.append([row.get(header, '') for header in headers])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def build_dataset_id(scale: str, seed: int, theme_count: int, segments_per_theme: int, suffix: str = '') -> str:
    suffix_part = f'_{suffix}' if suffix else ''
    return f'{scale}_seed{seed}_t{theme_count}_s{segments_per_theme}{suffix_part}'


def resolve_path_from_repo(value: Optional[str], default_path: Path) -> Path:
    if not value:
        return default_path
    raw = Path(value)
    if raw.is_absolute():
        return raw
    return (REPO_ROOT / raw).resolve()

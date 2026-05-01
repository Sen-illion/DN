from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from openpyxl import Workbook


THIS_DIR = Path(__file__).resolve().parent
ABLATION_ROOT = THIS_DIR
EXPERIMENT_ROOT = ABLATION_ROOT.parents[1]
REPO_ROOT = ABLATION_ROOT.parents[2]
DEFAULT_SOURCE_EXPERIMENT_ROOT = REPO_ROOT / "DN-experiment-2.0"
DEFAULT_THEMES_PATH = REPO_ROOT / "game_themes_100.json"
DEFAULT_CONFIG_PATH = ABLATION_ROOT / "configs" / "context_ablation_config.json"
DEFAULT_OUTPUT_ROOT = ABLATION_ROOT / "outputs"


DEFAULT_GROUPS: Dict[str, Dict[str, Any]] = {
    "prompt_only": {
        "label": "Prompt only",
        "prompt_strategy": "provided",
        "use_previous_image": False,
        "description": "Use the stored LLM-generated image prompt only and do not pass the previous scene image.",
    },
    "prev_image_only": {
        "label": "Prev image only",
        "prompt_strategy": "minimal_base",
        "use_previous_image": True,
        "description": "Use a minimal base instruction plus the previous scene image; do not use the full LLM-rich prompt.",
    },
    "prompt_plus_prev_image": {
        "label": "Prompt + prev image",
        "prompt_strategy": "provided",
        "use_previous_image": True,
        "description": "Use both the stored LLM-generated image prompt and the previous scene image.",
    },
}

DEFAULT_SCALE_PRESETS: Dict[str, Dict[str, int]] = {
    "pilot": {"max_games": 3, "max_eval_segments_per_game": 3},
    "standard": {"max_games": 6, "max_eval_segments_per_game": 5},
    "full": {"max_games": 0, "max_eval_segments_per_game": 0},
}


@dataclass
class SegmentSource:
    segment_index: int
    json_path: Path
    image_path: Optional[Path]
    scene: str
    prompt: str
    prompt_json: Any
    image_url: str
    raw: Dict[str, Any]


@dataclass
class SourceGame:
    theme_id: int
    theme: str
    style_label_zh: str
    image_style: Dict[str, Any]
    game_id: str
    folder: Path
    manifest_path: Path
    segments: Dict[int, SegmentSource]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def as_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def auto_fit_columns(ws) -> None:
    for column_cells in ws.columns:
        max_len = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            cell_value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(cell_value))
        ws.column_dimensions[column_letter].width = min(max(max_len + 2, 12), 80)


def append_sheet(workbook: Workbook, title: str, rows: Sequence[Dict[str, Any]]) -> None:
    ws = workbook.create_sheet(title=title)
    if not rows:
        ws.append(["empty"])
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([as_cell(row.get(header)) for header in headers])
    auto_fit_columns(ws)


def make_key_value_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"key": key, "value": as_cell(value)} for key, value in payload.items()]


def load_theme_catalog(themes_path: Path) -> Dict[int, Dict[str, Any]]:
    payload = load_json(themes_path)
    items = payload.get("items") or []
    catalog: Dict[int, Dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        theme_id = item.get("id")
        if isinstance(theme_id, int):
            catalog[theme_id] = item
    return catalog


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if path.is_file():
        payload = load_json(path)
    else:
        payload = {}
    payload.setdefault("experiment_name", "generation_context_ablation")
    payload.setdefault("groups", DEFAULT_GROUPS)
    payload.setdefault("scales", DEFAULT_SCALE_PRESETS)
    payload.setdefault("selection", {})
    payload.setdefault("runtime", {})
    payload.setdefault("outputs", {})
    payload["selection"].setdefault("min_eval_segment_index", 2)
    payload["selection"].setdefault("require_source_prompt", True)
    payload["selection"].setdefault("require_source_images", True)
    payload["selection"].setdefault("require_previous_image", True)
    payload["runtime"].setdefault("minimal_prompt_instruction", "Generate the next story scene image for the same game world. Use the reference image as the main continuity context. Keep character appearance, outfit, palette, lighting, and key props as consistent as possible. No text, no watermark, no symbols, no garbled characters, no words.")
    payload["runtime"].setdefault("skip_cache_lookup", True)
    payload["runtime"].setdefault("use_cache", True)
    payload["runtime"].setdefault("skip_protagonist_reference", True)
    payload["runtime"].setdefault("default_style", "default")
    payload["outputs"].setdefault("dataset_dir_name", "datasets")
    payload["outputs"].setdefault("run_dir_name", "runs")
    return payload


def resolve_image_path(segment_json_path: Path, segment_payload: Dict[str, Any]) -> Optional[Path]:
    image_file = as_text(segment_payload.get("image_file")).strip()
    if image_file:
        candidate = segment_json_path.parent / image_file
        if candidate.is_file():
            return candidate.resolve()

    image_url = as_text(segment_payload.get("image_url")).strip()
    if not image_url:
        return None

    if image_url.startswith("/image_cache/") or image_url.startswith("image_cache/"):
        cache_name = Path(image_url.replace("\\", "/")).name
        candidate = REPO_ROOT / "image_cache" / cache_name
        return candidate.resolve() if candidate.is_file() else None

    if image_url.startswith(("http://", "https://")):
        cache_name = Path(urlparse(image_url).path).name
        if not cache_name:
            return None
        candidate = REPO_ROOT / "image_cache" / cache_name
        return candidate.resolve() if candidate.is_file() else None

    direct = Path(image_url)
    if direct.is_file():
        return direct.resolve()
    return None


def iter_source_game_dirs(experiment_root: Path) -> List[Path]:
    if not experiment_root.is_dir():
        return []
    return sorted(path for path in experiment_root.iterdir() if path.is_dir() and path.name.startswith("theme_"))


def discover_source_games(
    experiment_root: Path = DEFAULT_SOURCE_EXPERIMENT_ROOT,
    themes_path: Path = DEFAULT_THEMES_PATH,
) -> List[SourceGame]:
    theme_catalog = load_theme_catalog(themes_path)
    games: List[SourceGame] = []

    for game_dir in iter_source_game_dirs(experiment_root):
        manifest_candidates = sorted(game_dir.glob("*_manifest.json"))
        if not manifest_candidates:
            continue
        manifest_path = manifest_candidates[0]
        manifest = load_json(manifest_path)
        game_id = as_text(manifest.get("game_id") or game_dir.name).strip()
        theme_id = manifest.get("theme_item_id")
        if not isinstance(theme_id, int):
            continue
        theme_item = theme_catalog.get(theme_id)
        if not theme_item:
            continue

        segments: Dict[int, SegmentSource] = {}
        for segment_meta in manifest.get("segments") or []:
            if not isinstance(segment_meta, dict):
                continue
            segment_index = segment_meta.get("index") or segment_meta.get("segment_index")
            if not isinstance(segment_index, int):
                continue
            json_name = segment_meta.get("json") or segment_meta.get("json_file")
            if not json_name:
                continue
            json_path = game_dir / str(json_name)
            if not json_path.is_file():
                continue
            payload = load_json(json_path)
            image_path = resolve_image_path(json_path, payload)
            segments[segment_index] = SegmentSource(
                segment_index=segment_index,
                json_path=json_path.resolve(),
                image_path=image_path,
                scene=as_text(payload.get("scene")).strip(),
                prompt=as_text(payload.get("prompt")).strip(),
                prompt_json=payload.get("prompt_json"),
                image_url=as_text(payload.get("image_url")).strip(),
                raw=payload,
            )

        if not segments:
            continue

        games.append(
            SourceGame(
                theme_id=theme_id,
                theme=as_text(theme_item.get("theme")).strip(),
                style_label_zh=as_text(theme_item.get("style_label_zh")).strip(),
                image_style=theme_item.get("image_style") or {},
                game_id=game_id,
                folder=game_dir.resolve(),
                manifest_path=manifest_path.resolve(),
                segments=segments,
            )
        )

    return games


def contiguous_eval_segments(source_game: SourceGame, selection_config: Dict[str, Any]) -> List[int]:
    require_prompt = bool(selection_config.get("require_source_prompt", True))
    require_source_images = bool(selection_config.get("require_source_images", True))
    require_previous_image = bool(selection_config.get("require_previous_image", True))
    min_eval_segment_index = int(selection_config.get("min_eval_segment_index", 2))

    eval_segments: List[int] = []
    segment_index = max(2, min_eval_segment_index)
    while True:
        current_segment = source_game.segments.get(segment_index)
        previous_segment = source_game.segments.get(segment_index - 1)
        if current_segment is None or previous_segment is None:
            break
        if not current_segment.scene:
            break
        if require_prompt and not current_segment.prompt:
            break
        if require_source_images and current_segment.image_path is None:
            break
        if require_previous_image and previous_segment.image_path is None:
            break
        eval_segments.append(segment_index)
        segment_index += 1
    return eval_segments


def flatten_task(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "sample_id": task["sample_id"],
        "dataset_name": task["dataset_name"],
        "group": task["group"],
        "theme_id": task["theme_id"],
        "theme": task["theme"],
        "style_label_zh": task["style_label_zh"],
        "game_id": task["game_id"],
        "segment_index": task["segment_index"],
        "previous_segment_index": task["previous_segment_index"],
        "needs_previous_image": task["needs_previous_image"],
        "source_segment_json": task["source_segment_json"],
        "source_segment_image": task["source_segment_image"],
        "source_previous_segment_image": task["source_previous_segment_image"],
        "source_prompt": task["source_prompt"],
        "source_scene": task["source_scene"],
        "run_parameters_snapshot": task["run_parameters_snapshot"],
    }


def build_dataset_manifest(
    *,
    scale: str,
    seed: int,
    config: Dict[str, Any],
    experiment_root: Path = DEFAULT_SOURCE_EXPERIMENT_ROOT,
    themes_path: Path = DEFAULT_THEMES_PATH,
    max_games_override: int = 0,
    max_eval_segments_override: int = 0,
    theme_ids_filter: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    scale_key = scale if scale in config.get("scales", {}) else "pilot"
    scale_cfg = dict(config.get("scales", {}).get(scale_key) or DEFAULT_SCALE_PRESETS[scale_key])
    selection_cfg = dict(config.get("selection", {}))
    groups_cfg = config.get("groups", DEFAULT_GROUPS)

    if max_games_override > 0:
        scale_cfg["max_games"] = int(max_games_override)
    if max_eval_segments_override > 0:
        scale_cfg["max_eval_segments_per_game"] = int(max_eval_segments_override)

    source_games = discover_source_games(experiment_root=experiment_root, themes_path=themes_path)
    normalized_theme_filter = sorted({int(theme_id) for theme_id in (theme_ids_filter or [])})
    if normalized_theme_filter:
        allowed_theme_ids = set(normalized_theme_filter)
        source_games = [source_game for source_game in source_games if source_game.theme_id in allowed_theme_ids]
    eligible_games: List[Tuple[SourceGame, List[int]]] = []
    for source_game in source_games:
        eval_segments = contiguous_eval_segments(source_game, selection_cfg)
        if eval_segments:
            eligible_games.append((source_game, eval_segments))

    rng = random.Random(seed)
    rng.shuffle(eligible_games)

    max_games = int(scale_cfg.get("max_games", 0) or 0)
    if max_games > 0:
        eligible_games = eligible_games[:max_games]

    tasks: List[Dict[str, Any]] = []
    selected_games_summary: List[Dict[str, Any]] = []
    selected_eval_samples = 0
    group_order = list(groups_cfg.keys())
    dataset_name = f"generation_context_ablation_{scale_key}_seed{seed}"
    if normalized_theme_filter:
        suffix = "_".join(f"{theme_id:03d}" for theme_id in normalized_theme_filter)
        dataset_name = f"{dataset_name}_theme{suffix}"

    for source_game, eval_segments in eligible_games:
        max_eval_segments_per_game = int(scale_cfg.get("max_eval_segments_per_game", 0) or 0)
        if max_eval_segments_per_game > 0:
            eval_segments = eval_segments[:max_eval_segments_per_game]
        if not eval_segments:
            continue

        selected_games_summary.append(
            {
                "theme_id": source_game.theme_id,
                "theme": source_game.theme,
                "game_id": source_game.game_id,
                "eval_segment_indexes": eval_segments,
                "warmup_segment_range": f"1-{max(eval_segments)}",
                "source_folder": str(source_game.folder),
                "source_manifest": str(source_game.manifest_path),
            }
        )

        for segment_index in eval_segments:
            current_segment = source_game.segments[segment_index]
            previous_segment = source_game.segments[segment_index - 1]
            selected_eval_samples += 1
            sample_id = f"{source_game.game_id}_seg_{segment_index:03d}"
            for group_name, group_cfg in groups_cfg.items():
                task_id = f"{sample_id}__{group_name}"
                run_parameters_snapshot = {
                    "scale": scale_key,
                    "seed": seed,
                    "group": group_name,
                    "prompt_strategy": group_cfg.get("prompt_strategy"),
                    "use_previous_image": bool(group_cfg.get("use_previous_image", False)),
                    "skip_cache_lookup": bool(config.get("runtime", {}).get("skip_cache_lookup", True)),
                    "use_cache": bool(config.get("runtime", {}).get("use_cache", True)),
                    "default_style": config.get("runtime", {}).get("default_style", "default"),
                }
                tasks.append(
                    {
                        "task_id": task_id,
                        "sample_id": sample_id,
                        "dataset_name": dataset_name,
                        "group": group_name,
                        "theme_id": source_game.theme_id,
                        "theme": source_game.theme,
                        "style_label_zh": source_game.style_label_zh,
                        "image_style": source_game.image_style,
                        "game_id": source_game.game_id,
                        "segment_index": segment_index,
                        "previous_segment_index": segment_index - 1,
                        "needs_previous_image": bool(group_cfg.get("use_previous_image", False)),
                        "source_folder": str(source_game.folder),
                        "source_manifest": str(source_game.manifest_path),
                        "source_segment_json": str(current_segment.json_path),
                        "source_segment_image": str(current_segment.image_path) if current_segment.image_path else "",
                        "source_previous_segment_json": str(previous_segment.json_path),
                        "source_previous_segment_image": str(previous_segment.image_path) if previous_segment.image_path else "",
                        "source_prompt": current_segment.prompt,
                        "source_prompt_json": current_segment.prompt_json,
                        "source_scene": current_segment.scene,
                        "source_previous_scene": previous_segment.scene,
                        "run_parameters_snapshot": run_parameters_snapshot,
                    }
                )

    summary = {
        "generated_at_utc": now_utc_iso(),
        "dataset_name": dataset_name,
        "scale": scale_key,
        "seed": seed,
        "source_experiment_root": str(experiment_root),
        "themes_path": str(themes_path),
        "theme_ids_filter": normalized_theme_filter,
        "available_source_games": len(source_games),
        "eligible_source_games": len(eligible_games),
        "selected_games": len(selected_games_summary),
        "selected_eval_samples": selected_eval_samples,
        "selected_tasks": len(tasks),
        "group_order": group_order,
        "scale_config": scale_cfg,
        "selection_config": selection_cfg,
    }

    return {
        "summary": summary,
        "config_snapshot": config,
        "selected_games": selected_games_summary,
        "tasks": tasks,
    }


def dataset_output_dir(output_root: Path, dataset_name: str) -> Path:
    return output_root / "datasets" / dataset_name


def _group_specific_manifest(dataset_manifest: Dict[str, Any], group_name: str) -> Dict[str, Any]:
    tasks = [
        task
        for task in (dataset_manifest.get("tasks", []) or [])
        if as_text(task.get("group")).strip() == group_name
    ]
    group_summary = dict(dataset_manifest.get("summary", {}) or {})
    group_summary["group_filter"] = group_name
    group_summary["selected_tasks"] = len(tasks)
    group_summary["selected_eval_samples"] = len({as_text(task.get("sample_id")) for task in tasks})
    group_summary["group_specific_export"] = True
    return {
        "summary": group_summary,
        "config_snapshot": dataset_manifest.get("config_snapshot", {}),
        "selected_games": dataset_manifest.get("selected_games", []),
        "tasks": tasks,
    }


def _write_manifest_bundle(manifest_payload: Dict[str, Any], out_dir: Path, file_stem: str) -> Dict[str, Path]:
    tasks = [flatten_task(task) for task in manifest_payload.get("tasks", [])]
    summary_rows = make_key_value_rows(manifest_payload.get("summary", {}))
    config_rows = make_key_value_rows(
        {
            "groups": manifest_payload.get("config_snapshot", {}).get("groups", {}),
            "scales": manifest_payload.get("config_snapshot", {}).get("scales", {}),
            "selection": manifest_payload.get("config_snapshot", {}).get("selection", {}),
            "runtime": manifest_payload.get("config_snapshot", {}).get("runtime", {}),
        }
    )

    workbook_path = out_dir / f"{file_stem}.xlsx"
    workbook = Workbook()
    workbook.remove(workbook.active)
    append_sheet(workbook, "dataset_manifest", tasks)
    append_sheet(workbook, "selection_summary", summary_rows)
    append_sheet(workbook, "config_snapshot", config_rows)
    workbook.save(workbook_path)

    json_path = out_dir / f"{file_stem}.json"
    jsonl_path = out_dir / f"{file_stem}.jsonl"
    write_json(json_path, manifest_payload)
    write_jsonl(jsonl_path, tasks)

    return {
        "json": json_path,
        "jsonl": jsonl_path,
        "xlsx": workbook_path,
    }


def write_dataset_artifacts(dataset_manifest: Dict[str, Any], output_root: Path = DEFAULT_OUTPUT_ROOT) -> Dict[str, Path]:
    dataset_name = as_text(dataset_manifest.get("summary", {}).get("dataset_name") or "dataset")
    out_dir = dataset_output_dir(output_root, dataset_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    aggregate_outputs = _write_manifest_bundle(dataset_manifest, out_dir, "dataset_manifest")

    per_group_outputs: Dict[str, Dict[str, Path]] = {}
    for group_name in (dataset_manifest.get("summary", {}).get("group_order") or []):
        group_manifest = _group_specific_manifest(dataset_manifest, as_text(group_name))
        per_group_outputs[as_text(group_name)] = _write_manifest_bundle(
            group_manifest,
            out_dir,
            f"dataset_manifest.{as_text(group_name)}",
        )

    return {
        "output_dir": out_dir,
        "dataset_manifest_json": aggregate_outputs["json"],
        "dataset_manifest_jsonl": aggregate_outputs["jsonl"],
        "dataset_manifest_xlsx": aggregate_outputs["xlsx"],
        "group_output_dir": out_dir,
        "group_manifests": per_group_outputs,
    }

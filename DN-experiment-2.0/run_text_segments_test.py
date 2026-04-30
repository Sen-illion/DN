# -*- coding: utf-8 -*-
"""
?????????????? N ???????????????????

???????????
- ?? `llm_generate_global` ???????
- ???? `_generate_single_option` ????
- ???? `next_options[0]` ??

???????
- --worldview-constraint on|off
- --prev-scene-feedback on|off
- --output-root <path>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["EXPERIMENT_NO_COUNCIL"] = "1"

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

from src.characters.paths import generate_game_id
from src.llm.global_gen import llm_generate_global
from src.story.options import _generate_single_option

_EXPERIMENT_SAVE = _REPO_ROOT / "DN-experiment" / "experiment_save.py"
_spec = importlib.util.spec_from_file_location("dn_experiment_save", _EXPERIMENT_SAVE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"???? {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder
experiment_dir_name = _save_mod.experiment_dir_name

EXPERIMENT_SUBDIR = "DN-experiment-2.0"
DEFAULT_PRESET_THEME_IDS: List[int] = [1, 2, 3, 4, 5, 6, 12, 18, 54, 73]


def _load_themes(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not isinstance(items, list):
        return []
    return [x for x in items if isinstance(x, dict)]


def _merge_flow_update(global_state: dict, option_data: dict) -> None:
    flow_update = option_data.get("flow_update") or {}
    if not flow_update or not isinstance(flow_state := global_state.setdefault("flow_worldline", {}), dict):
        return
    if isinstance(flow_update, dict):
        flow_state.update(flow_update)


def _prompt_theme() -> str:
    try:
        return input("????????").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def run_one_theme_n_segments(
    item: Dict[str, Any],
    segment_count: int,
    *,
    text_only: bool,
    output_root: Path,
    worldview_constraint: str,
    prev_scene_feedback: str,
    theme_item_id_override: Optional[int] = None,
) -> Tuple[str, Path]:
    """??????? N ???? (game_id, ????)?"""
    theme = (item.get("theme") or "").strip()
    if not theme:
        raise ValueError("?????? theme")

    raw_id = theme_item_id_override if theme_item_id_override is not None else item.get("id")
    theme_item_id: Optional[int] = None
    if isinstance(raw_id, int):
        theme_item_id = raw_id
    elif isinstance(raw_id, str) and raw_id.strip().isdigit():
        theme_item_id = int(raw_id.strip())

    game_id = generate_game_id()
    protagonist_attr: Dict[str, Any] = {}
    difficulty = "??"
    tone_key = "normal_ending"

    global_state = llm_generate_global(theme, protagonist_attr, difficulty, tone_key)
    if not isinstance(global_state, dict):
        raise RuntimeError("???????")

    global_state["game_id"] = game_id
    global_state["user_theme"] = theme
    global_state["_skip_protagonist_reference"] = True
    global_state["_experiment_worldview_constraint"] = worldview_constraint
    global_state["_experiment_prev_scene_feedback"] = prev_scene_feedback
    if text_only:
        global_state["_skip_scene_image"] = True

    img_style = item.get("image_style")
    if img_style and isinstance(img_style, dict):
        global_state["image_style"] = img_style

    parent_scene_id: Any = "initial"
    prev_option_text = "????"

    for seg in range(1, segment_count + 1):
        result = _generate_single_option(0, prev_option_text, global_state)
        opt = result.get("data") if isinstance(result, dict) else None
        if not isinstance(opt, dict):
            raise RuntimeError(f"? {seg} ???????")

        save_segment_to_folder(
            _REPO_ROOT,
            game_id,
            seg,
            opt,
            global_state,
            theme_item_id=theme_item_id,
            option_text=prev_option_text,
            parent_scene_id=parent_scene_id,
            option_index=0,
            output_root=output_root,
            experiment_subdir=EXPERIMENT_SUBDIR,
        )

        _merge_flow_update(global_state, opt)

        if seg >= segment_count:
            break

        next_opts = opt.get("next_options") or []
        if not next_opts or not isinstance(next_opts, list):
            raise RuntimeError(f"? {seg} ???? next_options?????")
        choice = str(next_opts[0]).strip()
        if not choice:
            raise RuntimeError(f"? {seg} ????????")

        prev_img = opt.get("scene_image")
        prev_text = (opt.get("scene") or "").strip()
        global_state["_visual_context"] = {
            "sceneId": f"{game_id}_seg{seg}",
            "previousSceneImage": prev_img if isinstance(prev_img, dict) else {},
            "previousSceneText": prev_text,
        }
        parent_scene_id = f"{game_id}_seg{seg}"
        prev_option_text = choice

    dir_name = experiment_dir_name(game_id, theme_item_id)
    exp_dir = output_root / dir_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "game_id": game_id,
        "theme_item_id": theme_item_id,
        "theme": theme,
        "segment_count": segment_count,
        "text_only": text_only,
        "worldview_constraint": worldview_constraint,
        "prev_scene_feedback": prev_scene_feedback,
        "style_label_zh": item.get("style_label_zh"),
        "image_style": item.get("image_style"),
        "segments": [
            {
                "index": i,
                "json": f"{game_id}_{i:03d}.json",
            }
            for i in range(1, segment_count + 1)
        ],
    }
    (exp_dir / f"{game_id}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return game_id, exp_dir


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    ap = argparse.ArgumentParser(description="DN 2.0 ?????????")
    ap.add_argument("--themes-file", type=Path, default=_REPO_ROOT / "game_themes_100.json")
    ap.add_argument("--segments", type=int, default=10, help="????????? 10")
    ap.add_argument("--text-only", action="store_true", help="???????????")
    ap.add_argument("--worldview-constraint", choices=("on", "off"), default="on")
    ap.add_argument("--prev-scene-feedback", choices=("on", "off"), default="on")
    ap.add_argument("--output-root", type=Path, default=_REPO_ROOT / EXPERIMENT_SUBDIR)
    ap.add_argument("--theme", type=str, default="", help="????????")
    ap.add_argument("--theme-id", type=int, default=None, help="game_themes_100.json ?? id")
    ap.add_argument(
        "--preset-10",
        action="store_true",
        help=f"????? {len(DEFAULT_PRESET_THEME_IDS)} ??? id?{DEFAULT_PRESET_THEME_IDS}",
    )
    args = ap.parse_args()

    themes_path = args.themes_file
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    os.environ["EXPERIMENT_WORLDVIEW_CONSTRAINT"] = args.worldview_constraint
    os.environ["EXPERIMENT_PREV_SCENE_FEEDBACK"] = args.prev_scene_feedback

    if not themes_path.is_file():
        print(f"????????{themes_path}")
        return 2

    all_items = _load_themes(themes_path)
    by_id = {it.get("id"): it for it in all_items if isinstance(it.get("id"), int)}

    if args.preset_10:
        batch = []
        for tid in DEFAULT_PRESET_THEME_IDS:
            item = by_id.get(tid)
            if not item:
                print(f"?? id={tid} ???????????")
                continue
            batch.append(item)
        if not batch:
            print("??????")
            return 2
        for i, item in enumerate(batch, 1):
            tid = item.get("id", "?")
            tname = (item.get("theme") or "")[:50]
            print(f"\n=== [{i}/{len(batch)}] ?? id={tid} {tname!r} ===")
            try:
                gid, exp_dir = run_one_theme_n_segments(
                    item,
                    args.segments,
                    text_only=args.text_only,
                    output_root=output_root,
                    worldview_constraint=args.worldview_constraint,
                    prev_scene_feedback=args.prev_scene_feedback,
                )
                print(f"? ?? game_id={gid}")
                print(f"   ???{exp_dir.as_posix()}")
            except Exception as exc:
                print(f"? ?? id={tid}: {exc}")
                import traceback

                traceback.print_exc()
                return 1
        return 0

    theme_str = (args.theme or "").strip()
    if not theme_str:
        theme_str = _prompt_theme()
    if not theme_str:
        print("?????????--theme ?? ? --preset-10")
        return 2

    override_id = args.theme_id
    item: Dict[str, Any] = {"theme": theme_str, "image_style": None}
    if override_id is not None and override_id in by_id:
        item = dict(by_id[override_id])
    elif override_id is not None:
        item["id"] = override_id

    try:
        gid, exp_dir = run_one_theme_n_segments(
            item,
            args.segments,
            text_only=args.text_only,
            output_root=output_root,
            worldview_constraint=args.worldview_constraint,
            prev_scene_feedback=args.prev_scene_feedback,
            theme_item_id_override=override_id,
        )
        print(f"\n? ?? game_id={gid}")
        print(f"   ???{exp_dir.as_posix()}")
    except Exception as exc:
        print(f"? {exc}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

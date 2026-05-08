# -*- coding: utf-8 -*-
"""
简易实验：与 DN 主线一致的事件/场景分段逻辑（llm_generate_global + 链式 _generate_single_option），
每局连续生成 N 段剧情（默认 10 段），每段沿用「开始游戏 / 选 next_options[0]」与 run_batch_themes 相同的推进方式。

落盘目录：仓库根下 DN-experiment-2.0/，子目录名 theme_{主题编号:03d}_{game_id}/（与 DN-experiment 批处理一致），
每段 JSON：{game_id}_{segment:03d}.json。

用法示例：
  # 交互输入单个主题（10 段，纯文本较快）
  python DN-experiment-2.0/run_text_segments_test.py --segments 10 --text-only

  # 从 game_themes_100.json 跑预设 10 个不同画风样本（见 DEFAULT_PRESET_THEME_IDS）
  python DN-experiment-2.0/run_text_segments_test.py --preset-10 --text-only

  # 指定主题编号与条目标题（需与 JSON 中 id/theme 一致时可核对）
  python DN-experiment-2.0/run_text_segments_test.py --theme-id 7 --segments 10 --text-only
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
    raise RuntimeError(f"无法加载 {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder
experiment_dir_name = _save_mod.experiment_dir_name

EXPERIMENT_SUBDIR = "DN-experiment-2.0"

# 覆盖 game_themes_100.json 中 8 种 style_label_zh + 2 个补充主题（写实/动漫各多一条），共 10 条用于画风多样性抽检
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
        return input("请输入游戏主题：").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def run_one_theme_n_segments(
    item: Dict[str, Any],
    segment_count: int,
    *,
    text_only: bool,
    theme_item_id_override: Optional[int] = None,
) -> Tuple[str, Path]:
    """单主题连续 N 段，返回 (game_id, 实验目录)。"""
    theme = (item.get("theme") or "").strip()
    if not theme:
        raise ValueError("主题条目缺少 theme")

    raw_id = theme_item_id_override if theme_item_id_override is not None else item.get("id")
    theme_item_id: Optional[int] = None
    if isinstance(raw_id, int):
        theme_item_id = raw_id
    elif isinstance(raw_id, str) and raw_id.strip().isdigit():
        theme_item_id = int(raw_id.strip())

    game_id = generate_game_id()
    protagonist_attr: Dict[str, Any] = {}
    difficulty = "中等"
    tone_key = "normal_ending"

    global_state = llm_generate_global(theme, protagonist_attr, difficulty, tone_key)
    if not isinstance(global_state, dict):
        raise RuntimeError("世界观生成失败")

    global_state["game_id"] = game_id
    global_state["user_theme"] = theme
    global_state["_skip_protagonist_reference"] = True
    if text_only:
        global_state["_skip_scene_image"] = True

    img_style = item.get("image_style")
    if img_style and isinstance(img_style, dict):
        global_state["image_style"] = img_style

    parent_scene_id: Any = "initial"
    prev_option_text = "开始游戏"

    for seg in range(1, segment_count + 1):
        r = _generate_single_option(0, prev_option_text, global_state)
        opt = r.get("data") if isinstance(r, dict) else None
        if not isinstance(opt, dict):
            raise RuntimeError(f"第 {seg} 段剧情生成失败")

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
            experiment_subdir=EXPERIMENT_SUBDIR,
        )

        _merge_flow_update(global_state, opt)

        if seg >= segment_count:
            break

        next_opts = opt.get("next_options") or []
        if not next_opts or not isinstance(next_opts, list):
            raise RuntimeError(f"第 {seg} 段未返回 next_options，无法继续")
        choice = str(next_opts[0]).strip()
        if not choice:
            raise RuntimeError(f"第 {seg} 段第一个选项为空")

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
    exp_dir = _REPO_ROOT / EXPERIMENT_SUBDIR / dir_name

    manifest = {
        "game_id": game_id,
        "theme_item_id": theme_item_id,
        "theme": theme,
        "segment_count": segment_count,
        "text_only": text_only,
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

    ap = argparse.ArgumentParser(description="DN 2.0 实验：N 段剧情 JSON，落盘 DN-experiment-2.0")
    ap.add_argument("--themes-file", type=Path, default=_REPO_ROOT / "game_themes_100.json")
    ap.add_argument("--segments", type=int, default=10, help="连续剧情段数，默认 10")
    ap.add_argument("--text-only", action="store_true", help="跳过场景图，仅 LLM 文本（推荐测试文案）")
    ap.add_argument("--theme", type=str, default="", help="直接指定主题文案（不配 --theme-id 时目录无 theme_ 编号前缀）")
    ap.add_argument("--theme-id", type=int, default=None, help="game_themes_100.json 中的 id，用于目录 theme_XXX_ 命名")
    ap.add_argument(
        "--preset-10",
        action="store_true",
        help=f"从主题表跑 {len(DEFAULT_PRESET_THEME_IDS)} 条预设 id：{DEFAULT_PRESET_THEME_IDS}",
    )
    args = ap.parse_args()

    themes_path = args.themes_file
    if not themes_path.is_file():
        print(f"找不到主题文件：{themes_path}")
        return 2

    all_items = _load_themes(themes_path)
    by_id = {it.get("id"): it for it in all_items if isinstance(it.get("id"), int)}

    if args.preset_10:
        batch = []
        for tid in DEFAULT_PRESET_THEME_IDS:
            it = by_id.get(tid)
            if not it:
                print(f"预设 id={tid} 在主题表中不存在，跳过")
                continue
            batch.append(it)
        if not batch:
            print("预设批次为空")
            return 2
        for i, item in enumerate(batch):
            tid = item.get("id", "?")
            tname = (item.get("theme") or "")[:50]
            print(f"\n=== [{i + 1}/{len(batch)}] 主题 id={tid} {tname!r} ===")
            try:
                gid, exp_dir = run_one_theme_n_segments(
                    item,
                    args.segments,
                    text_only=args.text_only,
                )
                print(f"✅ 完成 game_id={gid}")
                print(f"   目录：{exp_dir.as_posix()}")
            except Exception as e:
                print(f"❌ 失败 id={tid}: {e}")
                import traceback

                traceback.print_exc()
                return 1
        return 0

    theme_str = (args.theme or "").strip()
    if not theme_str:
        theme_str = _prompt_theme()
    if not theme_str:
        print("未输入主题。可用：--theme 文案 或 --preset-10")
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
            theme_item_id_override=override_id,
        )
        print(f"\n✅ 完成 game_id={gid}")
        print(f"   目录：{exp_dir.as_posix()}")
    except Exception as e:
        print(f"❌ {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""
批量：从 game_themes_100.json 顺序取多个主题，每主题 2 段连续剧情 + 各 1 张图，
落盘到 DN-experiment/theme_{主题编号:03d}_{game_id}/ 下，文件名为 {game_id}_001.* / {game_id}_002.* 。

示例：
  python -u DN-experiment/run_batch_themes.py --offset 0
  python -u DN-experiment/run_batch_themes.py --offset 3 --count 3
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

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

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

from src.characters.paths import generate_game_id
from src.llm.global_gen import llm_generate_global
from src.story.options import _generate_single_option

_EXPERIMENT_SAVE = Path(__file__).resolve().parent / "experiment_save.py"
_spec = importlib.util.spec_from_file_location("dn_experiment_save", _EXPERIMENT_SAVE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"无法加载 {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder
experiment_dir_name = _save_mod.experiment_dir_name


def _load_themes(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not isinstance(items, list):
        return []
    return items


def _merge_flow_update(global_state: dict, option_data: dict) -> None:
    flow_update = option_data.get("flow_update") or {}
    if not flow_update or not isinstance(flow_state := global_state.setdefault("flow_worldline", {}), dict):
        return
    if isinstance(flow_update, dict):
        flow_state.update(flow_update)


def run_one_theme_two_segments(repo_root: Path, item: dict) -> tuple[str, Path]:
    """返回 (game_id, 该局目录)。"""
    theme = (item.get("theme") or "").strip()
    theme_item_id = item.get("id")
    if not theme:
        raise ValueError("主题条目缺少 theme")

    game_id = generate_game_id()
    protagonist_attr = {}
    difficulty = "中等"
    tone_key = "normal_ending"

    global_state = llm_generate_global(theme, protagonist_attr, difficulty, tone_key)
    if not isinstance(global_state, dict):
        raise RuntimeError("世界观生成失败")

    global_state["game_id"] = game_id
    global_state["user_theme"] = theme
    # 实验批处理：不等待主角立绘、不把主角三视图作为生图参考（与正式游戏不同）
    global_state["_skip_protagonist_reference"] = True
    img_style = item.get("image_style")
    if img_style and isinstance(img_style, dict):
        global_state["image_style"] = img_style

    # 段 1：开始游戏
    r1 = _generate_single_option(0, "开始游戏", global_state)
    opt1 = r1.get("data") if isinstance(r1, dict) else None
    if not isinstance(opt1, dict):
        raise RuntimeError("第 1 段剧情生成失败")

    save_segment_to_folder(
        repo_root,
        game_id,
        1,
        opt1,
        global_state,
        theme_item_id=theme_item_id if isinstance(theme_item_id, int) else None,
        option_text="开始游戏",
        parent_scene_id="initial",
        option_index=0,
    )

    _merge_flow_update(global_state, opt1)

    next_opts = opt1.get("next_options") or []
    if not next_opts or not isinstance(next_opts, list):
        raise RuntimeError("第 1 段未返回 next_options，无法生成第 2 段")
    choice2 = str(next_opts[0]).strip()
    if not choice2:
        raise RuntimeError("第 1 段第一个选项为空")

    # 与线上一致的视觉连续性
    prev_img = opt1.get("scene_image")
    prev_text = (opt1.get("scene") or "").strip()
    global_state["_visual_context"] = {
        "sceneId": f"{game_id}_seg1",
        "previousSceneImage": prev_img if isinstance(prev_img, dict) else {},
        "previousSceneText": prev_text,
    }

    r2 = _generate_single_option(0, choice2, global_state)
    opt2 = r2.get("data") if isinstance(r2, dict) else None
    if not isinstance(opt2, dict):
        raise RuntimeError("第 2 段剧情生成失败")

    save_segment_to_folder(
        repo_root,
        game_id,
        2,
        opt2,
        global_state,
        theme_item_id=theme_item_id if isinstance(theme_item_id, int) else None,
        option_text=choice2,
        parent_scene_id=f"{game_id}_seg1",
        option_index=0,
    )

    exp_dir = repo_root / "DN-experiment" / experiment_dir_name(
        game_id,
        theme_item_id if isinstance(theme_item_id, int) else None,
    )
    return game_id, exp_dir


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    ap = argparse.ArgumentParser(description="批量主题：每主题 2 段剧情 + 图，统一 {game_id}_001/_002 命名")
    ap.add_argument("--offset", type=int, default=0, help="在 items 中的起始下标（0-based）")
    ap.add_argument("--count", type=int, default=3, help="本次处理的主题数量，默认 3")
    ap.add_argument(
        "--themes-file",
        type=Path,
        default=_REPO_ROOT / "game_themes_100.json",
        help="主题列表 JSON 路径",
    )
    args = ap.parse_args()

    themes_path = args.themes_file
    if not themes_path.is_file():
        print(f"找不到主题文件：{themes_path}")
        return 2

    items = _load_themes(themes_path)
    n = len(items)
    if args.offset < 0 or args.offset >= n:
        print(f"offset 无效：{args.offset}，当前共 {n} 条主题")
        return 2
    if args.offset + args.count > n:
        print(
            f"主题数量不足：offset={args.offset}, count={args.count} 需要到索引 {args.offset + args.count - 1}，"
            f"但只有 {n} 条（索引 0..{n - 1}）"
        )
        return 2

    batch = items[args.offset : args.offset + args.count]
    repo_root = _REPO_ROOT

    for i, item in enumerate(batch):
        if not isinstance(item, dict):
            print(f"跳过非 dict 条目：{item!r}")
            continue
        tid = item.get("id", "?")
        tname = (item.get("theme") or "")[:40]
        print(f"\n=== [{i + 1}/{len(batch)}] 主题 id={tid} {tname!r} ===")
        try:
            game_id, exp_dir = run_one_theme_two_segments(repo_root, item)
            print(f"✅ 完成 game_id={game_id}")
            print(f"   目录：{exp_dir.as_posix()}")
            print(f"   {game_id}_001.json / {game_id}_002.json (+ 配图)")
        except Exception as e:
            print(f"❌ 失败 id={tid}: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

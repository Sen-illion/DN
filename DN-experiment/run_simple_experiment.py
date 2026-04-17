# -*- coding: utf-8 -*-
"""
实验用最小链路（无选项交互）：
1) 让用户输入游戏主题
2) 复用 DN-main 的同一套 LLM 生成剧情文本 + 对应场景图
3) 将文本（含图片信息）以 JSON 形式保存到 DN-experiment/<game_id>/ 下

批量多主题、每主题双段剧情与 {game_id}_001/_002 统一命名：见同目录 run_batch_themes.py。

运行：
  python DN-experiment/run_simple_experiment.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import argparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Windows 下强制 UTF-8 输出，避免控制台 GBK 导致 Emoji/特殊符号报错
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 实验链路不启用 Council（群体智能）；世界观生成与后台补全都走单模型（见 EXPERIMENT_NO_COUNCIL）
os.environ["EXPERIMENT_NO_COUNCIL"] = "1"

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

from src.characters.paths import generate_game_id
from src.llm.global_gen import llm_generate_global
from src.story.options import _generate_single_option
from server.experiment_log import save_dn_experiment_bundle


def _prompt_theme() -> str:
    try:
        theme = input("请输入游戏主题：").strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    return theme


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", type=str, default="", help="游戏主题（不传则交互输入）")
    args = parser.parse_args()

    theme = (args.theme or "").strip() or _prompt_theme()
    if not theme:
        print("未输入主题，已退出。")
        return 2

    # 与 server 的 /generate-worldview 行为对齐：生成 game_id 并写入 global_state
    game_id = generate_game_id()
    protagonist_attr = {}
    difficulty = "中等"
    tone_key = "normal_ending"

    global_state = llm_generate_global(theme, protagonist_attr, difficulty, tone_key)
    if not isinstance(global_state, dict):
        print("世界观生成失败：global_state 非 dict。")
        return 1

    global_state["game_id"] = game_id
    global_state["user_theme"] = theme
    # 实验脚本：不等待主角立绘、剧情图不使用主角参考图
    global_state["_skip_protagonist_reference"] = True

    # 复用同一套“第一段剧情+生图”逻辑：等价于用户点击“开始游戏”
    result = _generate_single_option(0, "开始游戏", global_state)
    option_data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(option_data, dict):
        print("剧情生成失败：option_data 非 dict。")
        return 1

    # 保存到 DN-experiment/<game_id>/scene_00001.json（同 game_server.py 的记录逻辑）
    save_dn_experiment_bundle(
        option_data=option_data,
        global_state=global_state,
        option_index=0,
        option_text="开始游戏",
        parent_scene_id="initial",
    )

    # 尝试打印最新落盘的 JSON（便于实验定位）
    exp_dir = Path(__file__).resolve().parents[0] / game_id
    json_files = sorted(exp_dir.glob("scene_*.json"))
    if json_files:
        latest = json_files[-1]
        print(f"\n✅ 已保存：{latest.as_posix()}")
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
            print("---- 预览 ----")
            print(f"scene: {str(payload.get('scene', ''))[:200]}...")
            print(f"image_url: {payload.get('image_url', '')}")
        except Exception:
            pass
    else:
        print(f"\n✅ 已保存到：{exp_dir.as_posix()}（未找到 scene_*.json，可能 EXPERIMENT_LOG=0）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# -*- coding: utf-8 -*-
"""
根据 DN-experiment-2.0（或同结构）落盘的 JSON，用其中的「scene」字段走与线上一致的生图链路：

  src.image.api_providers.generate_scene_image(scene, global_state, ...)

流程简述：
1. 读取每条 JSON 的 scene、game_id、theme_item_id、segment_index 等；
2. 用 game_themes_100.json 里对应 id 的 image_style 填入 global_state（与跑剧情时一致）；
3. 可选：按段序链式设置 _visual_context（上一段的图 + 文本），与 run_batch_themes 类似，利于画风连续；
4. 将生成结果写回同目录 JSON，并把图片复制为 {game_id}_{NNN}.png（与 experiment_save 行为一致）。

依赖：与主项目相同，需在仓库根配置 .env（IMAGE_GENERATION_CONFIG / 各 provider Key），并从仓库根执行。

示例（在仓库根 DN-main 下）：

  python DN-experiment-2.0/generate_images_from_experiment_json.py ^
    --folder DN-experiment-2.0/theme_002_game_1776416045_g7umnm

  # 不串联上一张图（每段独立生图）
  python DN-experiment-2.0/generate_images_from_experiment_json.py --folder ... --no-chain
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

from src.image.api_providers import generate_scene_image

_EXPERIMENT_SAVE = _REPO_ROOT / "DN-experiment" / "experiment_save.py"
_spec = importlib.util.spec_from_file_location("dn_experiment_save", _EXPERIMENT_SAVE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"无法加载 {_EXPERIMENT_SAVE}")
_save_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_save_mod)
save_segment_to_folder = _save_mod.save_segment_to_folder


def _load_themes(path: Path) -> Dict[int, Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    out: Dict[int, Dict[str, Any]] = {}
    for it in items:
        if isinstance(it, dict) and isinstance(it.get("id"), int):
            out[it["id"]] = it
    return out


def _list_segment_jsons(folder: Path) -> List[Path]:
    files = sorted(folder.glob("game_*_*.json"), key=lambda p: p.name)
    # 排除 manifest
    return [p for p in files if "manifest" not in p.name.lower()]


def _infer_experiment_subdir(theme_folder: Path) -> str:
    """theme_folder 形如 .../DN-experiment-2.0/theme_002_xxx → 返回 DN-experiment-2.0"""
    try:
        rel = theme_folder.resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        return "DN-experiment-2.0"
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return "DN-experiment-2.0"


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    ap = argparse.ArgumentParser(description="根据实验 JSON 中的 scene 字段补生成场景图")
    ap.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="含 game_*_*.json 的目录（如 DN-experiment-2.0/theme_002_game_xxx）",
    )
    ap.add_argument(
        "--themes-file",
        type=Path,
        default=_REPO_ROOT / "game_themes_100.json",
        help="用于按 theme_item_id 取 image_style",
    )
    ap.add_argument(
        "--no-chain",
        action="store_true",
        help="不传入上一段剧情图作参考（每段独立；默认会链式参考上一张）",
    )
    ap.add_argument(
        "--skip-cache-lookup",
        action="store_true",
        help="传给 generate_scene_image(skip_cache_lookup=True)，强制不命中旧缓存（补图时常用）",
    )
    ap.add_argument(
        "--experiment-subdir",
        type=str,
        default="",
        help="相对仓库根的实验根目录名，默认根据 --folder 推断（一般为 DN-experiment-2.0）",
    )
    args = ap.parse_args()

    folder = args.folder
    if not folder.is_dir():
        print(f"目录不存在：{folder}")
        return 2

    themes_path = args.themes_file
    if not themes_path.is_file():
        print(f"找不到主题表：{themes_path}")
        return 2
    by_id = _load_themes(themes_path)

    json_files = _list_segment_jsons(folder)
    if not json_files:
        print(f"未找到 game_*_*.json：{folder}")
        return 2

    prev_scene_image: Dict[str, Any] = {}
    prev_scene_text = ""

    for jp in json_files:
        data = json.loads(jp.read_text(encoding="utf-8"))
        game_id = (data.get("game_id") or "").strip()
        scene = (data.get("scene") or "").strip()
        seg = int(data.get("segment_index") or 0)
        theme_item_id = data.get("theme_item_id")
        tid = int(theme_item_id) if isinstance(theme_item_id, int) else None

        if not game_id or not scene:
            print(f"跳过（缺 game_id 或 scene）：{jp.name}")
            continue

        item = by_id.get(tid) if tid is not None else None
        global_state: Dict[str, Any] = {
            "game_id": game_id,
            "tone": "normal_ending",
            "core_worldview": {},
            "flow_worldline": {},
            "_skip_protagonist_reference": True,
        }
        if item and isinstance(item.get("image_style"), dict):
            global_state["image_style"] = item["image_style"]
        if not args.no_chain and prev_scene_image.get("url"):
            global_state["_visual_context"] = {
                "sceneId": f"{game_id}_seg{max(0, seg - 1)}",
                "previousSceneImage": prev_scene_image,
                "previousSceneText": prev_scene_text,
            }

        suffix = f"{game_id}_seg{seg}"
        scene_image = generate_scene_image(
            scene,
            global_state,
            "default",
            use_cache=True,
            cache_key_suffix=suffix,
            skip_cache_lookup=args.skip_cache_lookup,
        )
        if not scene_image or not isinstance(scene_image, dict) or not scene_image.get("url"):
            print(f"❌ 生图失败：{jp.name}")
            return 1

        prompt_json = global_state.get("_last_scene_prompt_json")
        url = str(scene_image.get("url") or "").strip()
        pr = str(scene_image.get("prompt") or "").strip()
        scene_payload = {
            "url": url,
            "prompt": pr,
            "style": scene_image.get("style", "default"),
            "width": scene_image.get("width", 1024),
            "height": scene_image.get("height", 1024),
            "cached": scene_image.get("cached", False),
            "image_type": "story_scene",
        }
        if prompt_json is not None:
            scene_payload["prompt_json"] = prompt_json

        option_data: Dict[str, Any] = {
            "scene": scene,
            "sceneId": data.get("scene_id"),
            "scene_image": scene_payload,
        }

        exp_sub = (args.experiment_subdir or "").strip() or _infer_experiment_subdir(folder)
        save_segment_to_folder(
            _REPO_ROOT,
            game_id,
            seg,
            option_data,
            global_state,
            theme_item_id=tid,
            option_text=str(data.get("option") or ""),
            parent_scene_id=data.get("parent_scene_id") or "initial",
            option_index=int(data.get("option_id") or 0),
            experiment_subdir=exp_sub,
        )

        prev_scene_image = scene_payload
        prev_scene_text = scene
        print(f"✅ {jp.name} → 已写入配图与 JSON")

    print(f"\n完成，共处理 {len(json_files)} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

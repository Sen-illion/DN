# -*- coding: utf-8 -*-
"""
每局游戏在仓库内 DN-experiment/<game_id>/ 下记录「一次选项 → 整段 scene」的 JSON 与配图副本。
可通过环境变量 EXPERIMENT_LOG=0 关闭。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from server.config import IMAGE_CACHE_DIR

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.Lock()


def _experiment_enabled() -> bool:
    return os.getenv("EXPERIMENT_LOG", "1").strip() not in ("0", "false", "False", "no", "NO")


def _next_index(game_dir: Path) -> int:
    nums: list[int] = []
    for p in game_dir.glob("scene_*.json"):
        try:
            parts = p.stem.split("_", 1)
            if len(parts) == 2 and parts[0] == "scene":
                nums.append(int(parts[1]))
        except (ValueError, IndexError):
            continue
    return max(nums) + 1 if nums else 1


def _resolve_local_image(repo_root: Path, url: str) -> Optional[Path]:
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if u.startswith("/image_cache/") or u.startswith("image_cache/"):
        name = Path(u.replace("\\", "/")).name
        p = repo_root / IMAGE_CACHE_DIR / name
        return p if p.is_file() else None
    if u.startswith(("http://", "https://")):
        path = urlparse(u).path
        name = Path(path).name
        if name:
            p = repo_root / IMAGE_CACHE_DIR / name
            if p.is_file():
                return p
        return None
    return None


def save_dn_experiment_bundle(
    *,
    option_data: Dict[str, Any],
    global_state: Any,
    option_index: Any,
    option_text: str,
    parent_scene_id: Any,
) -> None:
    """
    将本段剧情文本与（若存在）展示用配图写入 DN-experiment/<game_id>/scene_NNNNN.json + 同主文件名图片。
    """
    if not _experiment_enabled():
        return
    if not isinstance(global_state, dict):
        return
    game_id = (global_state.get("game_id") or "").strip()
    if not game_id:
        return
    if not isinstance(option_data, dict):
        return

    scene_text = option_data.get("scene") or ""
    if not isinstance(scene_text, str):
        scene_text = str(scene_text)
    scene_image = option_data.get("scene_image")
    prompt = ""
    image_url = ""
    prompt_json: Any = None
    if isinstance(scene_image, dict):
        prompt = (scene_image.get("prompt") or "").strip()
        image_url = (scene_image.get("url") or "").strip()
        if "prompt_json" in scene_image:
            prompt_json = scene_image.get("prompt_json")

    new_scene_id = option_data.get("sceneId")

    try:
        oidx = int(option_index)
    except (TypeError, ValueError):
        oidx = option_index

    payload = {
        "game_id": game_id,
        "option_id": oidx,
        "option": (option_text or "").strip(),
        "parent_scene_id": parent_scene_id,
        "scene_id": new_scene_id,
        "prompt": prompt,
        "prompt_json": prompt_json,
        "scene": scene_text,
        "image_url": image_url,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    exp_root = _REPO_ROOT / "DN-experiment" / game_id
    with _LOCK:
        exp_root.mkdir(parents=True, exist_ok=True)
        idx = _next_index(exp_root)
        basename = f"scene_{idx:05d}"
        json_path = exp_root / f"{basename}.json"
        # 避免极端并发下覆盖：若已存在则顺延
        while json_path.exists():
            idx += 1
            basename = f"scene_{idx:05d}"
            json_path = exp_root / f"{basename}.json"

        src = _resolve_local_image(_REPO_ROOT, image_url)
        if src is None and image_url:
            payload["_note"] = "image not copied (no local file under image_cache)"

        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        if src is not None and src.is_file():
            ext = src.suffix.lower() or ".png"
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                ext = ".png"
            dest = exp_root / f"{basename}{ext}"
            shutil.copy2(src, dest)

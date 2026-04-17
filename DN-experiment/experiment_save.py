# -*- coding: utf-8 -*-
"""将单段剧情 JSON 与配图保存到 DN-experiment/ 下子目录，文件名为 {game_id}_{NNN}。

若有主题编号（如来自 game_themes_100.json 的 id），目录名为 theme_{编号:03d}_{game_id}；
否则仍为 <game_id>（无列表主题 id 的单次实验）。
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from server.config import IMAGE_CACHE_DIR


def experiment_dir_name(game_id: str, theme_item_id: Optional[int] = None) -> str:
    """
    DN-experiment 子目录名：有主题编号时为 theme_004_game_xxx，否则为 game_xxx。
    """
    if theme_item_id is not None and isinstance(theme_item_id, int):
        return f"theme_{theme_item_id:03d}_{game_id}"
    return game_id


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


def _ext_from_content_type(ct: str) -> str:
    ct = (ct or "").split(";")[0].strip().lower()
    if "png" in ct:
        return ".png"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    if "webp" in ct:
        return ".webp"
    if "gif" in ct:
        return ".gif"
    return ""


def _ext_from_url(url: str) -> str:
    suf = Path(urlparse(url).path).suffix.lower()
    if suf in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return ".jpg" if suf == ".jpeg" else suf
    return ""


def _download_image_to(url: str, dest_stem: Path, timeout: int = 120) -> Path:
    """下载到 dest_stem + 合适后缀，返回最终文件路径。dest_stem 不含扩展名。"""
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    url_ext = _ext_from_url(url)
    ct_ext = _ext_from_content_type(r.headers.get("Content-Type", ""))
    ext = url_ext or ct_ext or ".jpg"
    final = dest_stem.parent / f"{dest_stem.name}{ext}"
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(r.content)
    return final


def save_segment_to_folder(
    repo_root: Path,
    game_id: str,
    segment_index: int,
    option_data: Dict[str, Any],
    global_state: Dict[str, Any],
    *,
    theme_item_id: Optional[int] = None,
    option_text: str = "",
    parent_scene_id: Any = "initial",
    option_index: int = 0,
) -> Tuple[Path, Optional[Path]]:
    """
    写入 DN-experiment/<dir>/{game_id}_{segment_index:03d}.json 与同名图片（若可取得）。
    <dir> 见 experiment_dir_name（有 theme_item_id 时含主题编号前缀）。
    segment_index: 1 或 2（对应 _001 / _002）。
    """
    if not game_id or not isinstance(option_data, dict):
        raise ValueError("game_id / option_data 无效")

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

    try:
        oidx = int(option_index)
    except (TypeError, ValueError):
        oidx = option_index

    stem = f"{game_id}_{segment_index:03d}"
    dir_name = experiment_dir_name(game_id, theme_item_id)
    exp_dir = repo_root / "DN-experiment" / dir_name
    exp_dir.mkdir(parents=True, exist_ok=True)
    json_path = exp_dir / f"{stem}.json"

    protagonist_canonical = global_state.get("protagonist_canonical") if isinstance(global_state, dict) else None

    payload: Dict[str, Any] = {
        "game_id": game_id,
        "experiment_folder": dir_name,
        "segment_index": segment_index,
        "theme_item_id": theme_item_id,
        "option_id": oidx,
        "option": (option_text or "").strip(),
        "parent_scene_id": parent_scene_id,
        "scene_id": option_data.get("sceneId"),
        "prompt": prompt,
        "prompt_json": prompt_json,
        "scene": scene_text,
        "image_url": image_url,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if protagonist_canonical and isinstance(protagonist_canonical, dict):
        payload["protagonist_canonical"] = protagonist_canonical

    img_dest: Optional[Path] = None
    src = _resolve_local_image(repo_root, image_url)
    if src is not None and src.is_file():
        ext = src.suffix.lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            ext = ".png"
        img_dest = exp_dir / f"{stem}{ext}"
        shutil.copy2(src, img_dest)
        payload["image_file"] = img_dest.name
    elif image_url and str(image_url).startswith(("http://", "https://")):
        try:
            img_dest = _download_image_to(str(image_url), exp_dir / stem)
            if img_dest.is_file():
                payload["image_file"] = img_dest.name
        except Exception as ex:
            payload["_note"] = f"image download failed: {ex}"
            img_dest = None
    else:
        if image_url:
            payload["_note"] = "image not available locally and not https or no file"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return json_path, img_dest

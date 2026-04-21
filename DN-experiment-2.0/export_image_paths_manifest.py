# -*- coding: utf-8 -*-
"""
为 DN-experiment-2.0 下每个游戏目录生成一份图片路径清单（{game_id}_image_paths.json）。

解析规则与 DN-experiment/export_clip_jsonl.py 一致：
- 优先同目录下 image_file 指向的文件；
- 否则若 image_url 为 https，尝试仓库 image_cache/ 下与 URL 同名的已缓存文件；
- 若 image_url 为 /image_cache/... 形式，解析为仓库内 image_cache 文件。

用法（在仓库根目录）：

  # 扫描 DN-experiment-2.0 下所有 theme_* 目录，每局写一份清单
  python DN-experiment-2.0/export_image_paths_manifest.py

  # 仅处理单个游戏文件夹
  python DN-experiment-2.0/export_image_paths_manifest.py --folder DN-experiment-2.0/theme_073_game_xxx
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

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

from server.config import IMAGE_CACHE_DIR


def _list_segment_jsons(folder: Path) -> List[Path]:
    # 仅 {game_id}_{段号三位}.json；勿用 game_*_*.json，否则会误匹配 *_image_paths.json
    files = sorted(folder.glob("game_*_[0-9][0-9][0-9].json"), key=lambda p: p.name)
    return [p for p in files if "manifest" not in p.name.lower()]


def _rel_posix(repo_root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _image_cache_by_url(repo_root: Path, image_url: str) -> Optional[Path]:
    if not image_url or not isinstance(image_url, str):
        return None
    u = image_url.strip()
    if u.startswith(("http://", "https://")):
        name = Path(urlparse(u).path).name
        if not name:
            return None
        p = repo_root / IMAGE_CACHE_DIR / name
        return p if p.is_file() else None
    if u.startswith("/image_cache/") or u.startswith("image_cache/"):
        name = Path(u.replace("\\", "/")).name
        p = repo_root / IMAGE_CACHE_DIR / name
        return p if p.is_file() else None
    return None


def _resolve_image_path(repo_root: Path, jp: Path, data: Dict[str, Any]) -> Tuple[Optional[Path], str]:
    """返回 (存在的本地路径, 说明来源)。"""
    img_name = (data.get("image_file") or "").strip()
    if img_name:
        cand = jp.parent / img_name
        if cand.is_file():
            return cand.resolve(), "same_dir_image_file"
    cached = _image_cache_by_url(repo_root, (data.get("image_url") or "").strip())
    if cached is not None:
        return cached.resolve(), "image_cache_from_url"
    return None, "missing"


def _segment_sort_key(jp: Path) -> Tuple[int, str]:
    try:
        data = json.loads(jp.read_text(encoding="utf-8"))
        seg = data.get("segment_index")
        if isinstance(seg, int):
            return (seg, jp.name)
    except Exception:
        pass
    return (0, jp.name)


def build_manifest_for_folder(repo_root: Path, game_folder: Path) -> Optional[Dict[str, Any]]:
    json_files = _list_segment_jsons(game_folder)
    if not json_files:
        return None
    json_files.sort(key=_segment_sort_key)

    game_id: str = ""
    theme_item_id: Any = None
    experiment_folder: str = ""

    segments_out: List[Dict[str, Any]] = []
    for jp in json_files:
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception as ex:
            segments_out.append(
                {
                    "segment_index": None,
                    "json_file": jp.name,
                    "error": f"read_json_failed: {ex}",
                }
            )
            continue

        if not game_id and isinstance(data.get("game_id"), str):
            game_id = data["game_id"].strip()
        if theme_item_id is None:
            theme_item_id = data.get("theme_item_id")
        if not experiment_folder and isinstance(data.get("experiment_folder"), str):
            experiment_folder = data["experiment_folder"].strip()

        seg_idx = data.get("segment_index")
        resolved, src = _resolve_image_path(repo_root, jp, data)
        rel = _rel_posix(repo_root, resolved) if resolved else None
        entry: Dict[str, Any] = {
            "segment_index": seg_idx,
            "json_file": jp.name,
            "image_file_field": (data.get("image_file") or "").strip() or None,
            "image_url": (data.get("image_url") or "").strip() or None,
            "resolution": src,
            "image_path_repo_relative": rel,
            "exists": resolved is not None and resolved.is_file(),
        }
        segments_out.append(entry)

    if not game_id:
        game_id = game_folder.name

    return {
        "game_id": game_id,
        "theme_item_id": theme_item_id,
        "experiment_folder": experiment_folder or game_folder.name,
        "game_directory_repo_relative": _rel_posix(repo_root, game_folder),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_file": f"{game_id}_image_paths.json",
        "segment_count": len(segments_out),
        "segments": segments_out,
    }


def iter_theme_game_dirs(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    out: List[Path] = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and p.name.startswith("theme_"):
            if _list_segment_jsons(p):
                out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="为每个游戏目录生成图片路径清单 JSON")
    ap.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT / "DN-experiment-2.0",
        help="实验根目录（默认 仓库根/DN-experiment-2.0）",
    )
    ap.add_argument(
        "--folder",
        type=Path,
        default=None,
        help="仅处理该游戏目录（含 game_*_*.json），不传则处理 --root 下全部 theme_*",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将写入的路径，不写文件",
    )
    args = ap.parse_args()

    repo_root = _REPO_ROOT
    targets: List[Path]
    if args.folder is not None:
        targets = [args.folder]
    else:
        targets = iter_theme_game_dirs(args.root)

    if not targets:
        print(f"未找到可处理的游戏目录：{args.root}")
        return 2

    written = 0
    for folder in targets:
        if not folder.is_dir():
            print(f"跳过（非目录）：{folder}")
            continue
        manifest = build_manifest_for_folder(repo_root, folder)
        if not manifest:
            print(f"跳过（无分段 JSON）：{folder}")
            continue
        gid = manifest["game_id"]
        out_path = folder / f"{gid}_image_paths.json"
        if args.dry_run:
            print(f"[dry-run] 将写入：{out_path.as_posix()}")
            written += 1
            continue
        out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ {_rel_posix(repo_root, out_path)}")
        written += 1

    print(f"\n完成，共 {written} 份清单。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

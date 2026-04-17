# -*- coding: utf-8 -*-
"""
将 DN-experiment 下所有实验段 JSON 汇总为一条 CLIP 测评用 JSONL（供 scripts/eval_clip_score.py --jsonl 使用）。

每条 JSON 需含剧情文本与本地图片：
- 优先使用同目录下 image_file 指向的文件；
- 若无 image_file 但有 image_url，则尝试使用仓库 image_cache/ 下与 URL 同名的已缓存文件。

用法（在仓库根目录）:
  python DN-experiment/export_clip_jsonl.py
  python DN-experiment/export_clip_jsonl.py -o DN-experiment/my_clip.jsonl --text-field scene

然后:
  pip install -r requirements-eval.txt
  python scripts/eval_clip_score.py --jsonl DN-experiment/my_clip.jsonl

无本地图时若 JSON 含 image_url（https），汇总行会写该 URL；eval_clip_score.py 已支持 http(s) 直接下载评测。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from server.config import IMAGE_CACHE_DIR


def _image_cache_path(repo_root: Path, image_url: str) -> Path | None:
    if not image_url or not isinstance(image_url, str):
        return None
    u = image_url.strip()
    if not u.startswith(("http://", "https://")):
        return None
    name = Path(urlparse(u).path).name
    if not name:
        return None
    p = repo_root / IMAGE_CACHE_DIR / name
    return p if p.is_file() else None


def _resolve_image_for_record(repo_root: Path, jp: Path, data: dict) -> Path | None:
    """返回本地存在的图片绝对路径，否则 None。"""
    img_name = (data.get("image_file") or "").strip()
    if img_name:
        cand = jp.parent / img_name
        if cand.is_file():
            return cand.resolve()
    url = (data.get("image_url") or "").strip()
    return _image_cache_path(repo_root, url)


def export_jsonl(
    repo_root: Path,
    dn_root: Path,
    out_path: Path,
    *,
    text_field: str,
) -> tuple[int, int]:
    """
    扫描 dn_root 下所有 .json，写出 jsonl。
    返回 (写入条数, 跳过条数)。
    """
    written = 0
    skipped = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base = out_path.parent.resolve()

    with out_path.open("w", encoding="utf-8", newline="\n") as out_f:
        for jp in sorted(dn_root.rglob("*.json")):
            if not jp.is_file():
                continue
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                skipped += 1
                continue
            if not isinstance(data, dict):
                skipped += 1
                continue
            text = (data.get(text_field) or "").strip()
            if not text:
                skipped += 1
                continue

            img_abs = _resolve_image_for_record(repo_root, jp, data)
            image_val: str | None = None
            if img_abs is not None:
                try:
                    rel_img = Path(img_abs).resolve().relative_to(base)
                    image_val = rel_img.as_posix()
                except ValueError:
                    image_val = str(Path(img_abs).resolve())
            else:
                url = (data.get("image_url") or "").strip()
                if url.startswith(("http://", "https://")):
                    image_val = url

            if not image_val:
                skipped += 1
                continue

            gid = (data.get("game_id") or "").strip() or jp.stem
            seg = data.get("segment_index")
            try:
                seg_n = int(seg) if seg is not None else 0
            except (TypeError, ValueError):
                seg_n = 0
            rec_id = f"{gid}_{seg_n:03d}" if seg_n else gid

            line_obj = {
                "image": image_val,
                "text": text,
                "id": rec_id,
                "source_json": str(jp.relative_to(repo_root)).replace("\\", "/"),
            }
            out_f.write(json.dumps(line_obj, ensure_ascii=False) + "\n")
            written += 1

    return written, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="汇总 DN-experiment JSON → CLIP 用 JSONL")
    parser.add_argument(
        "--dn-root",
        type=Path,
        default=_REPO_ROOT / "DN-experiment",
        help="扫描根目录（默认仓库 DN-experiment）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_REPO_ROOT / "DN-experiment" / "clip_eval_pairs.jsonl",
        help="输出 JSONL 路径",
    )
    parser.add_argument(
        "--text-field",
        choices=("scene", "prompt"),
        default="scene",
        help="与图片配对的文本字段：剧情用 scene（默认），生图提示用 prompt",
    )
    args = parser.parse_args()

    dn_root = args.dn_root.resolve()
    if not dn_root.is_dir():
        print(f"目录不存在：{dn_root}", file=sys.stderr)
        return 2

    out_path = args.output.resolve()
    n, sk = export_jsonl(_REPO_ROOT, dn_root, out_path, text_field=args.text_field)
    print(f"已写入 {n} 行 → {out_path.as_posix()}（跳过 {sk} 条：无文本或无可用图）")
    if n == 0:
        print(
            "提示：跳过原因多为 JSON 里没有 scene、且无可用图片（无本地 file/cache，且无 https image_url）。",
            file=sys.stderr,
        )
        return 1
    print("CLIP 命令示例：")
    print(f'  python scripts/eval_clip_score.py --jsonl "{out_path}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

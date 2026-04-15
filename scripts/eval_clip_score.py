# -*- coding: utf-8 -*-
"""
批量计算「图像 ↔ 文本」CLIP 余弦相似度（常称 CLIP Score，与 DreamFusion 等文生 3D/优化工作里用的度量同源思想）。

数据来源：默认扫描 initial/character_references/*/role_archives.json，
每条角色记录取 first_img_path 与所选文本字段配对。

用法（先安装 requirements-eval.txt）:
  pip install -r requirements-eval.txt
  python scripts/eval_clip_score.py
  python scripts/eval_clip_score.py --text-field first_appear_scene
  python scripts/eval_clip_score.py --root "C:/path/to/character_references"
  python scripts/eval_clip_score.py --jsonl data/scene_image_pairs.jsonl

自建「剧情/场景 ↔ 图」数据集（JSON Lines，UTF-8）：
  每行一个 JSON 对象，至少包含:
    "image": "相对本文件或绝对路径，指向本地图片"
    "text":  "与该图对应的剧情/场景描写（可与生图 prompt 不同）"
  可选: "id" 字符串，仅用于日志区分。

说明：
- 默认模型 ViT-B-32（open_clip 预训练），与常见论文可比性较好。
- first_prompt 多为英文标签，与 CLIP 预训练分布较匹配。
- first_appear_scene 常为中文长叙事；标准英文 CLIP 对中文语义对齐较弱，分数仅作相对参考，
  若要以中文剧情为主指标，可改用 Chinese-CLIP 等模型（需自行替换本脚本中的模型与预处理）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

import torch
from PIL import Image


def _clip_sim_one(
    model,
    preprocess,
    tokenizer,
    device: torch.device,
    img_path: Path,
    text: str,
) -> float:
    im = Image.open(img_path).convert("RGB")
    image = preprocess(im).unsqueeze(0).to(device)
    tokens = tokenizer([text[:2000]]).to(device)
    with torch.inference_mode():
        image_features = model.encode_image(image)
        text_features = model.encode_text(tokens)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return (image_features @ text_features.T).squeeze().item()


def _iter_role_records(archives_path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    with archives_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return
    for role_id, rec in data.items():
        if isinstance(rec, dict):
            yield str(role_id), rec


def _resolve_path(base_dir: Path, p: str | None) -> Path | None:
    if not p or not str(p).strip():
        return None
    path = Path(p)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path if path.is_file() else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="CLIP image–text similarity on role_archives.json")
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=None,
        help="自建数据集：JSON Lines 路径（每行 {\"image\",\"text\"}）。指定后不再扫描 role_archives",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=root / "initial" / "character_references",
        help="character_references 根目录（未使用 --jsonl 时有效）",
    )
    parser.add_argument(
        "--text-field",
        choices=("first_prompt", "first_appear_scene", "core_features"),
        default="first_prompt",
        help="与图片配对的文本字段（默认与生成提示对齐；剧情↔图建议 first_appear_scene）",
    )
    parser.add_argument(
        "--model",
        default="ViT-B-32",
        help="open_clip 模型名，如 ViT-B-32, ViT-L-14",
    )
    parser.add_argument(
        "--pretrained",
        default="laion2b_s34b_b79k",
        help="open_clip 预训练权重名",
    )
    parser.add_argument("--device", default=None, help="cuda / cpu，默认自动")
    args = parser.parse_args()

    try:
        import open_clip
    except ImportError:
        print("缺少依赖：请先执行 pip install -r requirements-eval.txt", file=sys.stderr)
        return 1

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    model, _, preprocess = open_clip.create_model_and_transforms(
        args.model,
        pretrained=args.pretrained,
    )
    model = model.to(device)
    model.eval()
    tokenizer = open_clip.get_tokenizer(args.model)

    scores: list[float] = []
    skipped = 0
    field = args.text_field

    if args.jsonl is not None:
        jl = args.jsonl.resolve()
        if not jl.is_file():
            print(f"找不到 JSONL：{jl}", file=sys.stderr)
            return 1
        base = jl.parent
        line_no = 0
        with jl.open(encoding="utf-8") as f:
            for line in f:
                line_no += 1
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if not isinstance(obj, dict):
                    skipped += 1
                    continue
                raw_img = obj.get("image") or obj.get("image_path") or obj.get("path")
                text = (obj.get("text") or obj.get("scene") or obj.get("caption") or "").strip()
                rid = obj.get("id")
                if rid is None or rid == "":
                    rid = line_no

                if not raw_img or not text:
                    skipped += 1
                    continue
                p = Path(str(raw_img).strip())
                if not p.is_absolute():
                    p = (base / p).resolve()
                if not p.is_file():
                    skipped += 1
                    continue
                try:
                    sim = _clip_sim_one(model, preprocess, tokenizer, device, p, text)
                except OSError:
                    skipped += 1
                    continue
                scores.append(sim)
                print(f"{sim:.4f}\tjsonl\t{rid}\t{p.name}")
    else:
        json_files = sorted(args.root.glob("**/role_archives.json"))
        if not json_files:
            print(f"未找到 role_archives.json：{args.root}", file=sys.stderr)
            return 1

        for jf in json_files:
            game_dir = jf.parent
            for role_id, rec in _iter_role_records(jf):
                raw_path = rec.get("first_img_path")
                if not raw_path:
                    skipped += 1
                    continue
                img_path = _resolve_path(game_dir, str(raw_path))
                text = (rec.get(field) or "").strip()
                if not text:
                    skipped += 1
                    continue
                if img_path is None:
                    skipped += 1
                    continue
                try:
                    sim = _clip_sim_one(model, preprocess, tokenizer, device, img_path, text)
                except OSError:
                    skipped += 1
                    continue
                scores.append(sim)
                print(f"{sim:.4f}\t{jf.parent.name}\t{role_id}\t{field}")

    n = len(scores)
    if n == 0:
        print("无有效样本。", file=sys.stderr)
        return 1
    import statistics

    mean = statistics.fmean(scores)
    stdev = statistics.stdev(scores) if n > 1 else 0.0
    print("---")
    print(f"n={n}  mean={mean:.4f}  std={stdev:.4f}  (skipped={skipped})  device={device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

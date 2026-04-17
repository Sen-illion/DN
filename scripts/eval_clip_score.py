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
  python scripts/eval_clip_score.py --jsonl pairs.jsonl -o clip_results.csv
  python scripts/eval_clip_score.py --jsonl pairs.jsonl --backend cn_clip -o clip_results.csv
  python scripts/eval_clip_score.py --jsonl pairs.jsonl -o clip_results.xlsx

自建「剧情/场景 ↔ 图」数据集（JSON Lines，UTF-8）：
  每行一个 JSON 对象，至少包含:
    "image": "本地路径（相对 JSONL 所在目录、或绝对路径），或 https?:// 开头的图片 URL（将下载后评测）"
    "text":  "与该图对应的剧情/场景描写（可与生图 prompt 不同）"
  可选: "image_url" 与 "image" 二选一（与 image 同为 URL 时优先 image）；"id" 字符串，仅用于日志区分。

说明：
- 默认后端 open_clip，模型 ViT-B-32（laion 预训练），与常见论文可比性较好。
- first_prompt 多为英文标签，与 CLIP 预训练分布较匹配。
- 中文长叙事建议加 --backend cn_clip（Chinese-CLIP，需 pip 安装 cn_clip；首次会从 Hugging Face 下载权重）。
- Chinese-CLIP 文本侧约 52 token，超长剧情会在 tokenizer 内截断，分数仍为组内相对比较。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import requests
import torch
from PIL import Image


def _clip_sim_one_pil(
    model,
    preprocess,
    tokenizer,
    device: torch.device,
    pil_im: Image.Image,
    text: str,
) -> float:
    image = preprocess(pil_im.convert("RGB")).unsqueeze(0).to(device)
    tokens = tokenizer([text[:2000]]).to(device)
    with torch.inference_mode():
        image_features = model.encode_image(image)
        text_features = model.encode_text(tokens)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return (image_features @ text_features.T).squeeze().item()


def _clip_sim_one(
    model,
    preprocess,
    tokenizer,
    device: torch.device,
    img_path: Path,
    text: str,
) -> float:
    return _clip_sim_one_pil(
        model, preprocess, tokenizer, device, Image.open(img_path), text
    )


def _cn_clip_sim_one_pil(
    model,
    preprocess,
    device: torch.device,
    pil_im: Image.Image,
    text: str,
) -> float:
    """Chinese-CLIP（OFA-Sys/cn_clip）：图文余弦相似度。"""
    import cn_clip.clip as clip

    image = preprocess(pil_im.convert("RGB")).unsqueeze(0).to(device)
    tokens = clip.tokenize(text or "").to(device)
    with torch.inference_mode():
        image_features = model.encode_image(image)
        text_features = model.encode_text(tokens)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return (image_features @ text_features.T).squeeze().item()


def _cn_clip_sim_one(
    model,
    preprocess,
    device: torch.device,
    img_path: Path,
    text: str,
) -> float:
    return _cn_clip_sim_one_pil(model, preprocess, device, Image.open(img_path), text)


def _resolve_device(device_arg: str | None) -> torch.device:
    if device_arg is None:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    d = torch.device(device_arg)
    if d.type == "cuda" and not torch.cuda.is_available():
        print("警告：CUDA 不可用，已改用 CPU。", file=sys.stderr)
        return torch.device("cpu")
    return d


def _load_pil_from_image_spec(raw: str, jsonl_parent: Path, timeout: int = 120) -> tuple[Image.Image, str]:
    """
    raw 为本地路径（相对 jsonl_parent 或绝对）或 http(s) URL。
    返回 (PIL.Image, 用于日志的简短名称)。
    """
    s = (raw or "").strip()
    if s.startswith(("http://", "https://")):
        r = requests.get(s, timeout=timeout)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        name = Path(urlparse(s).path).name or "remote.jpg"
        return im, name
    p = Path(s)
    if not p.is_absolute():
        p = (jsonl_parent / p).resolve()
    im = Image.open(p)
    return im, p.name


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


def _truncate_text(s: str, max_len: int = 8000) -> str:
    s = s or ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


_RESULT_COLUMNS = (
    "similarity",
    "sample_id",
    "image_label",
    "image_spec",
    "text",
    "source_type",
    "source_detail",
)


def _write_results_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(_RESULT_COLUMNS), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _RESULT_COLUMNS})


def _write_results_xlsx(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    summary: dict[str, Any],
) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as e:
        raise RuntimeError(
            "写出 .xlsx 需要 openpyxl：pip install openpyxl（或改用 --output 指向 .csv）"
        ) from e

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "clip_scores"
    ws.append(list(_RESULT_COLUMNS))
    for r in rows:
        ws.append([r.get(k, "") for k in _RESULT_COLUMNS])
    ws2 = wb.create_sheet("summary")
    for k, v in summary.items():
        ws2.append([k, v])
    wb.save(path)


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
        "--backend",
        choices=("open_clip", "cn_clip"),
        default="open_clip",
        help="open_clip=英文 CLIP（默认）；cn_clip=Chinese-CLIP（中文图文更匹配）",
    )
    parser.add_argument(
        "--model",
        default="ViT-B-32",
        help="open_clip 时：模型名，如 ViT-B-32, ViT-L-14（--backend cn_clip 时请用 --cn-model）",
    )
    parser.add_argument(
        "--pretrained",
        default="laion2b_s34b_b79k",
        help="open_clip 预训练权重名（仅 --backend open_clip）",
    )
    parser.add_argument(
        "--cn-model",
        default="ViT-B-16",
        metavar="NAME",
        help="Chinese-CLIP 模型：ViT-B-16, ViT-L-14, ViT-L-14-336, ViT-H-14, RN50（仅 --backend cn_clip）",
    )
    parser.add_argument(
        "--cn-download-root",
        type=Path,
        default=None,
        help="Chinese-CLIP 权重下载目录，默认 ~/.cache/clip",
    )
    parser.add_argument(
        "--cn-use-modelscope",
        action="store_true",
        help="从魔搭 ModelScope 下载权重（需 pip install modelscope；默认用 Hugging Face）",
    )
    parser.add_argument("--device", default=None, help="cuda / cpu，默认自动；若指定 cuda 但不可用则回退 CPU")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="结果表格：.csv（UTF-8 BOM，Excel 可直接打开）或 .xlsx（需 openpyxl）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="最多评测 N 条有效样本（成功算出相似度后计数），默认不限制",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("--limit 须为正整数", file=sys.stderr)
        return 2

    use_cn = args.backend == "cn_clip"
    tokenizer = None
    if use_cn:
        try:
            from cn_clip.clip import load_from_name
        except ImportError:
            print(
                "缺少 Chinese-CLIP：请执行 pip install cn_clip huggingface_hub",
                file=sys.stderr,
            )
            return 1
        device = _resolve_device(args.device)
        dl_root = str(args.cn_download_root) if args.cn_download_root is not None else None
        model, preprocess = load_from_name(
            args.cn_model,
            device=device,
            download_root=dl_root,
            use_modelscope=args.cn_use_modelscope,
        )
        model.eval()
    else:
        try:
            import open_clip
        except ImportError:
            print("缺少依赖：请先执行 pip install -r requirements-eval.txt", file=sys.stderr)
            return 1
        device = _resolve_device(args.device)
        model, _, preprocess = open_clip.create_model_and_transforms(
            args.model,
            pretrained=args.pretrained,
        )
        model = model.to(device)
        model.eval()
        tokenizer = open_clip.get_tokenizer(args.model)

    scores: list[float] = []
    rows: list[dict[str, Any]] = []
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
                raw_img = (
                    obj.get("image")
                    or obj.get("image_path")
                    or obj.get("path")
                    or obj.get("image_url")
                )
                text = (obj.get("text") or obj.get("scene") or obj.get("caption") or "").strip()
                rid = obj.get("id")
                if rid is None or rid == "":
                    rid = line_no

                if not raw_img or not text:
                    skipped += 1
                    continue
                raw_str = str(raw_img).strip()
                try:
                    pil_im, label = _load_pil_from_image_spec(raw_str, base)
                    if use_cn:
                        sim = _cn_clip_sim_one_pil(model, preprocess, device, pil_im, text)
                    else:
                        sim = _clip_sim_one_pil(
                            model, preprocess, tokenizer, device, pil_im, text
                        )
                except (OSError, requests.RequestException, ValueError):
                    skipped += 1
                    continue
                scores.append(sim)
                detail = (obj.get("source_json") or "").strip() or f"line {line_no}"
                rows.append(
                    {
                        "similarity": round(sim, 6),
                        "sample_id": str(rid),
                        "image_label": label,
                        "image_spec": raw_str,
                        "text": _truncate_text(text),
                        "source_type": "jsonl",
                        "source_detail": detail,
                    }
                )
                print(f"{sim:.4f}\tjsonl\t{rid}\t{label}")
                if args.limit is not None and len(scores) >= args.limit:
                    break
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
                    if use_cn:
                        sim = _cn_clip_sim_one(model, preprocess, device, img_path, text)
                    else:
                        sim = _clip_sim_one(
                            model, preprocess, tokenizer, device, img_path, text
                        )
                except OSError:
                    skipped += 1
                    continue
                scores.append(sim)
                rows.append(
                    {
                        "similarity": round(sim, 6),
                        "sample_id": str(role_id),
                        "image_label": img_path.name,
                        "image_spec": str(img_path),
                        "text": _truncate_text(text),
                        "source_type": "role_archives",
                        "source_detail": f"{jf.parent.name}/{role_id}",
                    }
                )
                print(f"{sim:.4f}\t{jf.parent.name}\t{role_id}\t{field}")
                if args.limit is not None and len(scores) >= args.limit:
                    break
            if args.limit is not None and len(scores) >= args.limit:
                break

    n = len(scores)
    if n == 0:
        print("无有效样本。", file=sys.stderr)
        return 1

    mean = statistics.fmean(scores)
    stdev = statistics.stdev(scores) if n > 1 else 0.0
    print("---")
    print(f"n={n}  mean={mean:.4f}  std={stdev:.4f}  (skipped={skipped})  device={device}")

    if args.output is not None:
        out = args.output.resolve()
        suf = out.suffix.lower()
        summary = {
            "n": n,
            "mean": round(mean, 6),
            "std": round(stdev, 6),
            "skipped": skipped,
            "device": str(device),
            "backend": args.backend,
            "model": args.cn_model if use_cn else args.model,
            "pretrained": "cn_clip_hub" if use_cn else args.pretrained,
            "limit": args.limit if args.limit is not None else "none",
        }
        try:
            if suf == ".csv":
                _write_results_csv(out, rows)
            elif suf in (".xlsx", ".xlsm"):
                _write_results_xlsx(out, rows, summary=summary)
            else:
                print(
                    f"--output 仅支持 .csv 或 .xlsx，当前后缀：{out.suffix}",
                    file=sys.stderr,
                )
                return 1
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f"已写入表格：{out.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

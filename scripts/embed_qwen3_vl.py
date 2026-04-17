# -*- coding: utf-8 -*-
"""
对 JSONL（与 export_clip_jsonl.py / eval_clip_score.py 相同格式）逐条做 Qwen3-VL-Embedding：
  - 文本侧：encode(剧情/提示)
  - 图像侧：encode(本地路径或 https URL)
  - 输出：图文余弦相似度 CSV；可选保存两组向量到 .npz

依赖（建议单独环境，版本以官方 README 为准）:
  pip install -r requirements-qwen3-vl-embed.txt

用法（在仓库根目录）:
  python scripts/embed_qwen3_vl.py --jsonl DN-experiment/clip_eval_pairs.jsonl -o DN-experiment/qwen3_vl_scores.csv
  python scripts/embed_qwen3_vl.py --jsonl DN-experiment/clip_eval_pairs.jsonl -o scores.csv --save-npz DN-experiment/qwen3_vl_emb.npz
  python scripts/embed_qwen3_vl.py --jsonl pairs.jsonl --model Qwen/Qwen3-VL-Embedding-8B --device cuda

无法访问 huggingface.co 时（WinError 10061 等）:
  PowerShell: $env:HF_ENDPOINT="https://hf-mirror.com"
  或本脚本: --hf-endpoint https://hf-mirror.com
  或先下载模型到本地目录，再: --model C:/path/to/Qwen3-VL-Embedding-2B

大文件下载读超时（read timed out）:
  本脚本默认已拉长 HF_HUB_DOWNLOAD_TIMEOUT；仍慢可加: --hf-download-timeout 86400
  或先: huggingface-cli download Qwen/Qwen3-VL-Embedding-2B --local-dir ...
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


def _resolve_image_spec(raw: str, jsonl_parent: Path) -> str:
    """返回传给 SentenceTransformer 的路径或 URL。"""
    s = (raw or "").strip()
    if s.startswith(("http://", "https://")):
        return s
    p = Path(s)
    if not p.is_absolute():
        p = (jsonl_parent / p).resolve()
    return str(p)


def _pairwise_cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)
    denom = np.maximum(denom, 1e-12)
    return np.sum(a * b, axis=-1) / denom


def _print_hf_network_help(exc: BaseException) -> None:
    print(
        f"从 Hugging Face 拉取模型失败: {exc!r}\n"
        "常见原因: 无法直连 huggingface.co（防火墙/地区网络）。可任选其一:\n"
        "  1) PowerShell: $env:HF_ENDPOINT=\"https://hf-mirror.com\"\n"
        "  2) 加参数: --hf-endpoint https://hf-mirror.com\n"
        "  3) 在有网络的机器用 huggingface-cli download 把模型拷到本地后 "
        "--model <本地目录>\n"
        "  4) 大文件下载中途超时: 加 --hf-download-timeout 86400 后重试（支持断点续传）\n"
        "（镜像站点以你网络环境为准；也可使用系统代理/VPN。）",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qwen3-VL-Embedding：对 JSONL 图文对编码并计算相似度"
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        required=True,
        help="每行 JSON：至少含 image, text（与 export_clip_jsonl 一致）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出 CSV（默认：<jsonl 同名>_qwen3_vl.csv）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-VL-Embedding-2B",
        help="Hugging Face 模型 id 或本地目录",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="cuda / cuda:0 / cpu（默认自动）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="encode 批大小；显存不足保持 1",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="自定义 instruction（默认用模型内置，见官方文档）",
    )
    parser.add_argument(
        "--save-npz",
        type=Path,
        default=None,
        help="可选：保存 text_embeddings / image_embeddings 与 id 等到 .npz",
    )
    parser.add_argument(
        "--hf-endpoint",
        type=str,
        default=None,
        help="设置 HF Hub 端点（无法直连 huggingface.co 时用镜像，如 https://hf-mirror.com）",
    )
    parser.add_argument(
        "--hf-download-timeout",
        type=int,
        default=7200,
        metavar="SEC",
        help="HF 下载单次读超时（秒），写入 HF_HUB_DOWNLOAD_TIMEOUT；大模型/慢网可设 86400。默认 7200。",
    )
    args = parser.parse_args()

    if args.hf_endpoint:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint.strip().rstrip("/")

    # huggingface_hub 在首次 import 时读入；必须在 import sentence_transformers 之前设置
    if args.hf_download_timeout > 0:
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(args.hf_download_timeout)

    jsonl_path = args.jsonl.resolve()
    if not jsonl_path.is_file():
        print(f"文件不存在：{jsonl_path}", file=sys.stderr)
        return 2

    out_csv = args.output
    if out_csv is None:
        out_csv = jsonl_path.with_name(jsonl_path.stem + "_qwen3_vl.csv")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(
            "导入 sentence_transformers 失败（不一定是未安装，请看下方原因）。\n"
            f"  当前 Python: {sys.executable}\n"
            f"  原因: {e!r}\n"
            "  请用同一解释器安装: python -m pip install -r requirements-qwen3-vl-embed.txt",
            file=sys.stderr,
        )
        raise SystemExit(2) from e

    device = args.device
    if device is None:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(
        f"加载模型 {args.model}（device={device}，HF_HUB_DOWNLOAD_TIMEOUT={os.environ.get('HF_HUB_DOWNLOAD_TIMEOUT', 'default')}s）…",
        file=sys.stderr,
    )
    try:
        model = SentenceTransformer(args.model, device=device)
    except OSError as e:
        _print_hf_network_help(e)
        raise SystemExit(3) from e
    except RuntimeError as e:
        if "client has been closed" in str(e).lower() or "10061" in str(e):
            _print_hf_network_help(e)
            raise SystemExit(3) from e
        raise
    except Exception as e:
        err = str(e).lower()
        if "10061" in str(e) or "connection" in err or "refused" in err:
            _print_hf_network_help(e)
            raise SystemExit(3) from e
        raise

    jsonl_parent = jsonl_path.parent
    rows_in: list[dict[str, Any]] = []
    texts: list[str] = []
    images: list[str] = []

    with jsonl_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"第 {line_no} 行 JSON 解析失败：{e}", file=sys.stderr)
                continue
            if not isinstance(obj, dict):
                continue
            text = (obj.get("text") or "").strip()
            img_raw = (obj.get("image") or "").strip()
            if not text or not img_raw:
                print(f"第 {line_no} 行跳过：缺少 text 或 image", file=sys.stderr)
                continue
            img_spec = _resolve_image_spec(img_raw, jsonl_parent)
            rows_in.append(obj)
            texts.append(text)
            images.append(img_spec)

    if not texts:
        print("没有可编码的行。", file=sys.stderr)
        return 1

    kw: dict[str, Any] = {
        "batch_size": max(1, args.batch_size),
        "show_progress_bar": True,
    }
    if args.prompt is not None:
        kw["prompt"] = args.prompt

    print(f"编码文本（{len(texts)} 条）…", file=sys.stderr)
    text_emb = model.encode(texts, **kw)
    print(f"编码图像（{len(images)} 条）…", file=sys.stderr)
    # 图像侧一般不用与查询相同的 task prompt；若需可后续扩展第二个 prompt
    image_kw = {k: v for k, v in kw.items() if k != "prompt"}
    image_emb = model.encode(images, **image_kw)

    text_emb = np.asarray(text_emb)
    image_emb = np.asarray(image_emb)
    sims = _pairwise_cosine(text_emb, image_emb)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "similarity",
        "id",
        "source_json",
        "image",
        "text_len",
    )
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, obj in enumerate(rows_in):
            w.writerow(
                {
                    "similarity": f"{float(sims[i]):.6f}",
                    "id": (obj.get("id") or "") if isinstance(obj.get("id"), (str, int)) else "",
                    "source_json": (obj.get("source_json") or ""),
                    "image": (obj.get("image") or ""),
                    "text_len": len(texts[i]),
                }
            )

    print(f"已写入 {len(rows_in)} 行 → {out_csv}", file=sys.stderr)

    if args.save_npz is not None:
        ids = []
        for obj in rows_in:
            iid = obj.get("id")
            ids.append(str(iid) if iid is not None else "")
        np.savez(
            args.save_npz,
            text_embeddings=text_emb.astype(np.float32),
            image_embeddings=image_emb.astype(np.float32),
            similarity=sims.astype(np.float32),
            ids=np.array(ids, dtype=object),
        )
        print(f"已保存向量 → {args.save_npz.resolve()}", file=sys.stderr)

    mean_s = float(np.mean(sims))
    print(f"similarity 均值: {mean_s:.6f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

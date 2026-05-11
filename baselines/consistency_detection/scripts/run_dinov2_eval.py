from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_DINOV2_REPO = REPO_ROOT / "baselines" / "consistency_detection" / "repos" / "dinov2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DINOv2 cosine similarity on image pairs.")
    parser.add_argument("--pairs-csv", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--out-summary", required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--model-name", default="dinov2_vits14")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-missing", action="store_true")
    parser.add_argument("--auto-clone", action="store_true")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_device(value: str) -> str:
    import torch

    if value == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return value


def build_model(model_name: str, device: str):
    import torch
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode

    if (LOCAL_DINOV2_REPO / "hubconf.py").is_file():
        sys.path.insert(0, str(LOCAL_DINOV2_REPO))
        model = torch.hub.load(str(LOCAL_DINOV2_REPO), model_name, source="local", pretrained=True)
    else:
        model = torch.hub.load("facebookresearch/dinov2", model_name, pretrained=True)
    model.eval()
    model.to(device)
    transform = transforms.Compose(
        [
            transforms.Resize(256, interpolation=InterpolationMode.BICUBIC),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    return model, transform


def image_feature(model, transform, image_path: Path, device: str, cache: dict[str, np.ndarray]) -> np.ndarray:
    import torch

    key = str(image_path.resolve())
    cached = cache.get(key)
    if cached is not None:
        return cached

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)
    with torch.inference_mode():
        feat = model(tensor)
    if isinstance(feat, (tuple, list)):
        feat = feat[0]
    feat = feat.squeeze(0).detach().cpu().float().numpy()
    norm = np.linalg.norm(feat)
    if norm > 0:
        feat = feat / norm
    cache[key] = feat
    return feat


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return float("nan")
    return float(np.dot(a, b) / denom)


def main() -> int:
    args = parse_args()
    rows = load_rows(Path(args.pairs_csv))
    if args.limit > 0:
        rows = rows[: args.limit]

    device = resolve_device(args.device)
    model, transform = build_model(args.model_name, device)
    feature_cache: dict[str, np.ndarray] = {}

    results: list[dict[str, Any]] = []
    scores: list[float] = []
    unique_images: set[str] = set()

    for row in rows:
        ref = Path(row["ref"])
        candidate = Path(row["candidate"])
        if args.skip_missing and (not ref.is_file() or not candidate.is_file()):
            continue

        ref_feat = image_feature(model, transform, ref, device, feature_cache)
        cand_feat = image_feature(model, transform, candidate, device, feature_cache)
        score = cosine(ref_feat, cand_feat)
        unique_images.add(str(ref.resolve()))
        unique_images.add(str(candidate.resolve()))
        scores.append(score)
        result = dict(row)
        result.update(
            {
                "metric": "dinov2_cosine",
                "model_name": args.model_name,
                "device": device,
                "score": score,
            }
        )
        results.append(result)

    write_jsonl(Path(args.out_jsonl), results)

    summary = {
        "metric": "dinov2_cosine",
        "model_name": args.model_name,
        "device": device,
        "processed_rows": len(results),
        "unique_image_count": len(unique_images),
        "score_mean": float(np.mean(scores)) if scores else None,
        "score_std_population": float(np.std(scores)) if scores else None,
        "score_min": float(np.min(scores)) if scores else None,
        "score_max": float(np.max(scores)) if scores else None,
    }
    write_json(Path(args.out_summary), summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

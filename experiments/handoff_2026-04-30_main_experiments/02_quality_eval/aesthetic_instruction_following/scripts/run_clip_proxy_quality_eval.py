# -*- coding: utf-8 -*-
"""Run an automatic CLIP+CV proxy evaluation for formal20 visual quality.

This is a real, fully reproducible automatic measurement over the fixed manifest.
It is intended as a fallback/proxy when VLM-as-judge API access is unavailable.
Do not describe it as human or VLM judging in the paper.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import torch
from PIL import Image, ImageStat
from skimage import color, exposure, filters
from transformers import CLIPModel, CLIPProcessor

REPO_ROOT = Path(__file__).resolve().parents[5]
PKG_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = PKG_DIR / "results"

MANIFEST_PATH = RESULTS_DIR / "quality_eval_manifest_formal20_v1.jsonl"
GROUPS_PATH = RESULTS_DIR / "quality_eval_groups_formal20_v1.json"
INSTRUCTION_OUT = RESULTS_DIR / "per_image_instruction_following_scores.jsonl"
AESTHETIC_OUT = RESULTS_DIR / "per_group_aesthetic_consistency_scores.jsonl"
PROXY_DETAIL_OUT = RESULTS_DIR / "clip_proxy_quality_details.jsonl"

MODEL_ID = "openai/clip-vit-base-patch32"


STYLE_LABELS = {
    "realistic": "a realistic cinematic narrative scene, photographic, natural lighting",
    "cyberpunk": "a cyberpunk scene with neon lights, futuristic city, high-tech atmosphere",
    "ink_painting": "a traditional Chinese ink painting, brush strokes, monochrome wash",
    "watercolor": "a watercolor illustration with soft translucent colors",
    "anime": "an anime style illustration, clean line art, stylized character design",
    "oil_painting": "an oil painting with painterly texture and dramatic brushwork",
}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def repo_abs(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def l2_normalize(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True).clamp_min(1e-8)


def image_features(model: CLIPModel, pixel_values: torch.Tensor) -> torch.Tensor:
    # transformers 5.x returns base model outputs from get_image_features; use the
    # projection explicitly so the script remains compatible across versions.
    output = model.vision_model(pixel_values=pixel_values)
    return model.visual_projection(output.pooler_output)


def text_features(model: CLIPModel, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    output = model.text_model(input_ids=input_ids, attention_mask=attention_mask)
    return model.text_projection(output.pooler_output)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def score_1_5(value: float, low: float, high: float) -> float:
    if high <= low:
        return 3.0
    z = (value - low) / (high - low)
    return float(np.clip(1.0 + 4.0 * z, 1.0, 5.0))


def rounded(value: float) -> float:
    return round(float(value), 3)


def prompt_text(rec: Dict[str, Any]) -> str:
    parts = [
        f"theme: {rec.get('theme', '')}",
        f"style: {rec.get('image_style', {}).get('type', '')}",
        rec.get("generation_prompt", ""),
        rec.get("scene_text", ""),
    ]
    text = ". ".join(p for p in parts if p)
    # CLIP truncates to 77 tokens; keep the prompt front because it contains style and visual objects.
    return text[:1200]


def cv_features(path: Path) -> Dict[str, Any]:
    image = Image.open(path).convert("RGB").resize((256, 256))
    arr = np.asarray(image).astype(np.float32) / 255.0
    gray = color.rgb2gray(arr)
    hsv = color.rgb2hsv(arr)
    lap = filters.laplace(gray)
    sharpness = float(lap.var())
    hist, _ = np.histogram(gray, bins=64, range=(0, 1), density=True)
    hist = hist / max(hist.sum(), 1e-8)
    entropy = float(-(hist * np.log2(hist + 1e-8)).sum() / math.log2(64))
    saturation = float(hsv[:, :, 1].mean())
    brightness = float(gray.mean())
    dark_rate = float((gray < 0.04).mean())
    bright_rate = float((gray > 0.96).mean())
    rgb_stat = ImageStat.Stat(image)
    color_mean = np.array(rgb_stat.mean, dtype=np.float32) / 255.0
    color_std = np.array(rgb_stat.stddev, dtype=np.float32) / 255.0
    hist_rgb = []
    for channel in range(3):
        h, _ = np.histogram(arr[:, :, channel], bins=32, range=(0, 1), density=True)
        h = h / max(h.sum(), 1e-8)
        hist_rgb.append(h)
    color_hist = np.concatenate(hist_rgb)

    # Penalize blank/washed out/very blurry images but avoid over-penalizing deliberate low-key scenes.
    sharp_score = score_1_5(sharpness, 0.0002, 0.006)
    entropy_score = score_1_5(entropy, 0.35, 0.85)
    exposure_penalty = max(0.0, dark_rate - 0.45) + max(0.0, bright_rate - 0.20)
    exposure_score = float(np.clip(5.0 - 6.0 * exposure_penalty, 1.0, 5.0))
    quality_score = 0.40 * sharp_score + 0.35 * entropy_score + 0.25 * exposure_score
    return {
        "sharpness": sharpness,
        "entropy": entropy,
        "saturation": saturation,
        "brightness": brightness,
        "dark_rate": dark_rate,
        "bright_rate": bright_rate,
        "color_mean": color_mean,
        "color_std": color_std,
        "color_hist": color_hist,
        "cv_quality_score": float(np.clip(quality_score, 1.0, 5.0)),
    }


def load_model() -> Tuple[CLIPModel, CLIPProcessor, torch.device]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CLIPModel.from_pretrained(MODEL_ID, local_files_only=True).to(device)
    processor = CLIPProcessor.from_pretrained(MODEL_ID, local_files_only=True)
    model.eval()
    return model, processor, device


@torch.no_grad()
def embed_images(model: CLIPModel, processor: CLIPProcessor, device: torch.device, paths: List[Path], batch_size: int) -> np.ndarray:
    out = []
    for start in range(0, len(paths), batch_size):
        batch_paths = paths[start:start + batch_size]
        images = [Image.open(path).convert("RGB") for path in batch_paths]
        inputs = processor(images=images, return_tensors="pt").to(device)
        feats = l2_normalize(image_features(model, inputs["pixel_values"]))
        out.append(feats.cpu().numpy())
    return np.concatenate(out, axis=0)


@torch.no_grad()
def embed_texts(model: CLIPModel, processor: CLIPProcessor, device: torch.device, texts: List[str], batch_size: int) -> np.ndarray:
    out = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        inputs = processor(text=batch, padding=True, truncation=True, return_tensors="pt").to(device)
        feats = l2_normalize(text_features(model, inputs["input_ids"], inputs["attention_mask"]))
        out.append(feats.cpu().numpy())
    return np.concatenate(out, axis=0)


def percentile_range(values: List[float], lo: float = 5, hi: float = 95) -> Tuple[float, float]:
    return float(np.percentile(values, lo)), float(np.percentile(values, hi))


def color_hist_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Histogram intersection in [0, 1].
    return float(np.minimum(a, b).sum() / max(a.sum(), b.sum(), 1e-8))


def style_rank_score(image_emb: np.ndarray, style_text_embs: Dict[str, np.ndarray], expected: str) -> Tuple[float, str]:
    expected = expected or "realistic"
    if expected not in style_text_embs:
        expected = "realistic"
    sims = {name: cosine(image_emb, emb) for name, emb in style_text_embs.items()}
    ordered = sorted(sims.items(), key=lambda x: x[1], reverse=True)
    rank = [name for name, _ in ordered].index(expected) + 1
    best = ordered[0][0]
    if rank == 1:
        score = 5.0
    elif rank == 2:
        score = 4.0
    elif rank == 3:
        score = 3.0
    elif rank == 4:
        score = 2.0
    else:
        score = 1.0
    return score, best


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    records = read_jsonl(MANIFEST_PATH)
    paths = [repo_abs(rec["image_path"]) for rec in records]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing images: {missing[:5]}")

    model, processor, device = load_model()
    image_embs = embed_images(model, processor, device, paths, args.batch_size)
    text_embs = embed_texts(model, processor, device, [prompt_text(rec) for rec in records], args.batch_size)
    style_names = list(STYLE_LABELS)
    style_emb_array = embed_texts(model, processor, device, [STYLE_LABELS[name] for name in style_names], args.batch_size)
    style_text_embs = {name: style_emb_array[i] for i, name in enumerate(style_names)}

    cv_by_sample: Dict[str, Dict[str, Any]] = {}
    for rec, path in zip(records, paths):
        cv_by_sample[rec["sample_id"]] = cv_features(path)

    raw_clip = [cosine(image_embs[i], text_embs[i]) for i in range(len(records))]
    clip_lo, clip_hi = percentile_range(raw_clip)

    instruction_rows = []
    detail_rows = []
    emb_by_sample: Dict[str, np.ndarray] = {}
    rec_by_sample: Dict[str, Dict[str, Any]] = {}
    for i, rec in enumerate(records):
        sample_id = rec["sample_id"]
        emb_by_sample[sample_id] = image_embs[i]
        rec_by_sample[sample_id] = rec
        clip_score = score_1_5(raw_clip[i], clip_lo, clip_hi)
        style_score, detected_style = style_rank_score(image_embs[i], style_text_embs, rec.get("image_style", {}).get("type", "realistic"))
        cv_score = cv_by_sample[sample_id]["cv_quality_score"]
        forbidden_score = cv_score
        theme_alignment = 0.75 * clip_score + 0.25 * style_score
        text_image_alignment = clip_score
        constraint_coverage = 0.80 * clip_score + 0.20 * cv_score
        instruction_score = 0.35 * theme_alignment + 0.30 * text_image_alignment + 0.15 * style_score + 0.10 * constraint_coverage + 0.10 * forbidden_score
        tags = []
        if clip_score < 2.5:
            tags.append("low_clip_text_image_similarity")
        if style_score < 3:
            tags.append(f"style_rank_mismatch_detected_as_{detected_style}")
        if cv_score < 2.5:
            tags.append("low_cv_image_quality")
        instruction_rows.append({
            "sample_id": sample_id,
            "system": rec["system"],
            "benchmark_id": rec["benchmark_id"],
            "turn_type": rec["turn_type"],
            "judge_model": "openai/clip-vit-base-patch32+cv_proxy",
            "judge_id": "clip_proxy_v1",
            "theme_alignment": rounded(theme_alignment),
            "text_image_alignment": rounded(text_image_alignment),
            "style_following": rounded(style_score),
            "constraint_coverage": rounded(constraint_coverage),
            "forbidden_violation": rounded(forbidden_score),
            "instruction_following_score": rounded(instruction_score),
            "failure_tags": tags,
            "reason": "Automatic proxy: CLIP image-text similarity plus zero-shot style rank and CV artifact checks.",
        })
        detail = {k: v for k, v in cv_by_sample[sample_id].items() if not isinstance(v, np.ndarray)}
        detail_rows.append({
            "sample_id": sample_id,
            "system": rec["system"],
            "benchmark_id": rec["benchmark_id"],
            "turn_type": rec["turn_type"],
            "clip_image_text_cosine": rounded(raw_clip[i]),
            "clip_score_1_5": rounded(clip_score),
            "detected_style": detected_style,
            **{k: rounded(v) for k, v in detail.items()},
        })

    groups = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    aesthetic_rows = []
    for group_key, sample_ids in sorted(groups.items()):
        sample_ids = [sid for sid in sample_ids if sid in emb_by_sample]
        if not sample_ids:
            continue
        embs = [emb_by_sample[sid] for sid in sample_ids]
        cvs = [cv_by_sample[sid] for sid in sample_ids]
        clip_pairs = []
        color_pairs = []
        for a in range(len(sample_ids)):
            for b in range(a + 1, len(sample_ids)):
                clip_pairs.append(cosine(embs[a], embs[b]))
                color_pairs.append(color_hist_similarity(cvs[a]["color_hist"], cvs[b]["color_hist"]))
        clip_consistency = float(np.mean(clip_pairs)) if clip_pairs else 1.0
        color_consistency = float(np.mean(color_pairs)) if color_pairs else 1.0
        cv_quality = float(np.mean([cv["cv_quality_score"] for cv in cvs]))
        style_lighting = 1.0 + 4.0 * (0.55 * color_consistency + 0.45 * np.clip((clip_consistency - 0.55) / 0.35, 0, 1))
        subject_attr = score_1_5(clip_consistency, 0.55, 0.90)
        scene_world = 0.65 * subject_attr + 0.35 * style_lighting
        composition = cv_quality
        artifact = cv_quality
        aesthetic = 0.25 * style_lighting + 0.25 * subject_attr + 0.25 * scene_world + 0.15 * composition + 0.10 * artifact
        tags = []
        if style_lighting < 2.5:
            tags.append("low_style_lighting_consistency")
        if subject_attr < 2.5:
            tags.append("low_clip_cross_turn_consistency")
        if artifact < 2.5:
            tags.append("group_low_cv_quality")
        system, benchmark_id = group_key.split("::", 1)
        aesthetic_rows.append({
            "group_key": group_key,
            "system": system,
            "benchmark_id": benchmark_id,
            "sample_ids": sample_ids,
            "judge_model": "openai/clip-vit-base-patch32+cv_proxy",
            "judge_id": "clip_proxy_v1",
            "style_lighting_consistency": rounded(style_lighting),
            "subject_attribute_consistency": rounded(subject_attr),
            "scene_world_consistency": rounded(scene_world),
            "composition_quality": rounded(composition),
            "artifact_rate": rounded(artifact),
            "aesthetic_consistency_score": rounded(aesthetic),
            "failure_tags": tags,
            "reason": "Automatic proxy: cross-turn CLIP embedding consistency, color-histogram consistency, and CV quality checks.",
        })

    write_jsonl(INSTRUCTION_OUT, instruction_rows)
    write_jsonl(AESTHETIC_OUT, aesthetic_rows)
    write_jsonl(PROXY_DETAIL_OUT, detail_rows)
    print(json.dumps({
        "instruction_rows": len(instruction_rows),
        "aesthetic_rows": len(aesthetic_rows),
        "clip_similarity_percentile_5": rounded(clip_lo),
        "clip_similarity_percentile_95": rounded(clip_hi),
        "instruction_out": str(INSTRUCTION_OUT),
        "aesthetic_out": str(AESTHETIC_OUT),
        "details_out": str(PROXY_DETAIL_OUT),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

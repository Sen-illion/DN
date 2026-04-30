"""Shared helpers for DN-style baseline runners.

The runners intentionally keep upstream baseline repositories untouched. They
load a DN benchmark subset, create a timestamped run directory, and write
machine-readable artifacts for every sample even when a baseline is blocked.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import time
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Iterable


DEFAULT_NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, missing fingers, extra fingers, text, "
    "watermark, signature, blurry, cropped, worst quality, low quality"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: str | os.PathLike[str]) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | os.PathLike[str], payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_subset(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    data = load_json(path)
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError(f"Subset must be a list or object with items: {path}")
    return data


def make_run_dir(output: str | os.PathLike[str], baseline: str, run_id: str | None) -> Path:
    if not run_id:
        run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output) / f"{baseline}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * pct
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    frac = idx - lower
    return ordered[lower] * (1 - frac) + ordered[upper] * frac


def get_gpu_info() -> dict[str, Any]:
    info: dict[str, Any] = {"available": False, "name": None, "count": 0}
    try:
        import torch

        info["available"] = bool(torch.cuda.is_available())
        info["count"] = int(torch.cuda.device_count())
        info["torch"] = torch.__version__
        info["torch_cuda"] = torch.version.cuda
        if info["available"]:
            info["name"] = torch.cuda.get_device_name(0)
    except Exception as exc:  # pragma: no cover - depends on remote env
        info["error"] = repr(exc)
    return info


def environment_payload() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "hf_home": os.environ.get("HF_HOME"),
        "transformers_cache": os.environ.get("TRANSFORMERS_CACHE"),
        "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
        "gpu": get_gpu_info(),
    }


def style_name(item: dict[str, Any]) -> str:
    raw = item.get("image_style", {})
    style_type = raw.get("type") if isinstance(raw, dict) else str(raw)
    if style_type and "anime" in style_type.lower():
        return "Japanese Anime"
    if style_type and "comic" in style_type.lower():
        return "Comic book"
    return "Photographic"


def image_style_phrase(item: dict[str, Any]) -> str:
    raw = item.get("image_style", {})
    style_type = raw.get("type") if isinstance(raw, dict) else str(raw)
    if style_type and "anime" in style_type.lower():
        return "anime key visual, clean line art, expressive character acting"
    if style_type and "comic" in style_type.lower():
        return "comic book panel, clear composition, readable action"
    return "cinematic realistic scene, grounded lighting, coherent environment"


def build_visual_prompts(item: dict[str, Any], scene_count: int = 4) -> dict[str, Any]:
    """Create deterministic English-first prompts from a DN benchmark item."""

    theme = item.get("theme", item.get("benchmark_id", "DN story"))
    genre = item.get("expected_genre", "interactive narrative")
    tone = item.get("expected_tone", "dramatic")
    constraints = item.get("must_have_constraints", [])
    constraints_text = "; ".join(str(x) for x in constraints[:3])
    style = image_style_phrase(item)
    character = (
        f"[Protagonist] a consistent main character in a {genre} story, "
        f"visually grounded in the theme '{theme}', {style}"
    )
    scene_templates = [
        "opening scene introducing the world and the protagonist's immediate problem",
        "the protagonist discovers a concrete conflict and must make a decision",
        "tension escalates as the environment reveals a hidden risk",
        "a playable turning point with a clear action choice and strong atmosphere",
        "a later scene showing consequences while preserving character identity",
        "a closing cliffhanger scene that keeps the same protagonist recognizable",
    ]
    prompts: list[str] = []
    for idx, template in enumerate(scene_templates[:scene_count], start=1):
        prompts.append(
            f"[Protagonist] {template}; theme: {theme}; genre: {genre}; "
            f"tone: {tone}; constraints: {constraints_text}; {style} "
            f"# Scene {idx} for {theme}"
        )
    return {
        "character_description": character,
        "prompts": prompts,
        "style_name": style_name(item),
        "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
    }


def result_payload(
    item: dict[str, Any],
    baseline: str,
    status: str,
    prompts: list[str],
    latency_s: float | None = None,
    image_paths: list[str] | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "baseline": baseline,
        "benchmark_id": item.get("benchmark_id"),
        "theme": item.get("theme"),
        "status": status,
        "latency_s": latency_s,
        "prompt_list": prompts,
        "image_paths": image_paths or [],
        "error": error,
        "gpu": get_gpu_info(),
        "hf_home": os.environ.get("HF_HOME"),
    }
    if extra:
        payload.update(extra)
    return payload


def write_failure(sample_dir: Path, item: dict[str, Any], baseline: str, prompts: list[str], exc: BaseException) -> dict[str, Any]:
    payload = result_payload(
        item,
        baseline,
        "failed",
        prompts,
        error=f"{type(exc).__name__}: {exc}",
        extra={"traceback": traceback.format_exc()},
    )
    write_json(sample_dir / "result.json", payload)
    return payload


def summarize_results(run_dir: Path, baseline: str, results: list[dict[str, Any]], notes: str = "") -> dict[str, Any]:
    latencies = [float(r["latency_s"]) for r in results if r.get("status") == "success" and r.get("latency_s") is not None]
    success = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "failed"]
    blocked = [r for r in results if r.get("status") == "blocked"]
    images_per_success = [len(r.get("image_paths") or []) for r in success]
    summary = {
        "baseline": baseline,
        "sample_size": len(results),
        "success_count": len(success),
        "failed_count": len(failed),
        "blocked_count": len(blocked),
        "success_rate": round(len(success) / len(results), 4) if results else 0.0,
        "mean_latency_s": round(statistics.mean(latencies), 3) if latencies else None,
        "p95_latency_s": round(percentile(latencies, 0.95), 3) if latencies else None,
        "mean_images_per_sample": round(statistics.mean(images_per_success), 3) if images_per_success else 0,
        "oom_count": sum("out of memory" in str(r.get("error", "")).lower() for r in results),
        "failed_ids": [r.get("benchmark_id") for r in failed + blocked],
        "output_dir": str(run_dir),
        "notes": notes,
    }
    write_json(run_dir / "metrics.json", summary)
    write_json(run_dir / "summary.json", {"summary": summary, "results": results})
    write_summary_csv(run_dir / "summary.csv", summary)
    write_sample_index(run_dir / "sample_index.md", baseline, results)
    return summary


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    fields = [
        "baseline",
        "sample_size",
        "success_rate",
        "mean_latency_s",
        "p95_latency_s",
        "mean_images_per_sample",
        "failed_ids",
        "output_dir",
        "notes",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        row = {k: summary.get(k) for k in fields}
        row["failed_ids"] = ";".join(str(x) for x in summary.get("failed_ids", []))
        writer.writerow(row)


def write_sample_index(path: Path, baseline: str, results: list[dict[str, Any]]) -> None:
    lines = [f"# {baseline} Sample Index", ""]
    for result in results:
        lines.append(f"## {result.get('benchmark_id')} - {result.get('theme')}")
        lines.append("")
        lines.append(f"- status: `{result.get('status')}`")
        lines.append(f"- latency_s: `{result.get('latency_s')}`")
        if result.get("error"):
            lines.append(f"- error: `{result.get('error')}`")
        for image_path in result.get("image_paths") or []:
            lines.append(f"- image: `{image_path}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


@contextmanager
def tee_run_log(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as log:
        with redirect_stdout(log), redirect_stderr(log):
            yield


def common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--subset", required=True, help="Path to DN-style subset JSON.")
    parser.add_argument("--output", required=True, help="Base output directory.")
    parser.add_argument("--run-id", default=None, help="Optional run id. Defaults to timestamp.")
    parser.add_argument("--scene-count", type=int, default=4, help="Number of scene prompts per sample.")
    parser.add_argument("--seed", type=int, default=0)
    return parser


def save_pil_images(images: Iterable[Any], sample_dir: Path) -> list[str]:
    paths: list[str] = []
    for idx, image in enumerate(images, start=1):
        path = sample_dir / f"image_{idx:03d}.png"
        image.save(path)
        paths.append(str(path))
    return paths

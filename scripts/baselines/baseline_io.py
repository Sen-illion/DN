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
from typing import Any, Iterable


DEFAULT_NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, missing fingers, extra fingers, text, "
    "watermark, signature, blurry, cropped, worst quality, low quality"
)
DEFAULT_NEXT_TURN_ACTION = (
    "Choose the most direct action that advances the main conflict in the current scene."
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


def benchmark_brief(item: dict[str, Any]) -> dict[str, str]:
    theme = item.get("theme", item.get("benchmark_id", "DN story"))
    genre = item.get("expected_genre", "interactive narrative")
    tone = item.get("expected_tone", "dramatic")
    constraints = item.get("must_have_constraints", [])
    constraints_text = "; ".join(str(x) for x in constraints[:3])
    return {
        "theme": str(theme),
        "genre": str(genre),
        "tone": str(tone),
        "constraints_text": constraints_text,
        "style": image_style_phrase(item),
    }


def build_visual_prompts(item: dict[str, Any], scene_count: int = 4) -> dict[str, Any]:
    """Create deterministic English-first prompts from a DN benchmark item."""

    brief = benchmark_brief(item)
    character = (
        f"[Protagonist] a consistent main character in a {brief['genre']} story, "
        f"visually grounded in the theme '{brief['theme']}', {brief['style']}"
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
            f"[Protagonist] {template}; theme: {brief['theme']}; genre: {brief['genre']}; "
            f"tone: {brief['tone']}; constraints: {brief['constraints_text']}; {brief['style']} "
            f"# Scene {idx} for {brief['theme']}"
        )
    return {
        "character_description": character,
        "prompts": prompts,
        "style_name": style_name(item),
        "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
    }


def derive_previous_scene_summary(item: dict[str, Any], prompt_pack: dict[str, Any]) -> dict[str, str]:
    brief = benchmark_brief(item)
    first_prompt = (prompt_pack.get("prompts") or [""])[0]
    scene_setup = (
        f"A {brief['genre']} scene in '{brief['theme']}' establishes the opening conflict. "
        f"Visual target: {brief['style']}."
    )
    player_state = (
        f"The protagonist is inside the first beat of a {brief['tone']} story and must respond "
        "to the central conflict introduced in the opening image."
    )
    narrative_response = (
        "The current image represents the active playable state before the player clicks the next action. "
        f"Reference prompt: {first_prompt}"
    )
    suggested_next_step = DEFAULT_NEXT_TURN_ACTION
    return {
        "scene_setup": scene_setup,
        "player_state": player_state,
        "narrative_response": narrative_response,
        "suggested_next_step": suggested_next_step,
    }


def build_next_turn_prompt(
    item: dict[str, Any],
    prompt_pack: dict[str, Any],
    player_action: str = DEFAULT_NEXT_TURN_ACTION,
) -> dict[str, Any]:
    brief = benchmark_brief(item)
    previous_state = derive_previous_scene_summary(item, prompt_pack)
    continuation_prompt = (
        f"[Protagonist] continue the same world after the player action; theme: {brief['theme']}; "
        f"genre: {brief['genre']}; tone: {brief['tone']}; previous scene: {previous_state['scene_setup']}; "
        f"player state: {previous_state['player_state']}; player action: {player_action}; "
        f"show the immediate consequence of the chosen action; preserve the same protagonist, world logic, "
        f"and conflict continuity; {brief['style']} # Next turn for {brief['theme']}"
    )
    next_turn_hint = (
        "Render the next playable story image after the player chooses the most direct conflict-advancing action."
    )
    return {
        "player_action": player_action,
        "previous_state": previous_state,
        "continuation_prompt": continuation_prompt,
        "suggested_next_step": next_turn_hint,
    }


def build_input_bundle(
    item: dict[str, Any],
    prompt_pack: dict[str, Any],
    *,
    mode: str,
    player_action: str | None = None,
    previous_image_paths: list[str] | None = None,
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "original_dn_item": item,
        "mode": mode,
        "prompt_pack": prompt_pack,
        "baseline_parameters": {
            "scene_count": len(prompt_pack.get("prompts") or []),
            "negative_prompt": prompt_pack.get("negative_prompt"),
        },
    }
    if mode == "next_turn":
        player_action = player_action or DEFAULT_NEXT_TURN_ACTION
        continuation = build_next_turn_prompt(item, prompt_pack, player_action)
        bundle.update(
            {
                "player_action": player_action,
                "previous_image_paths": previous_image_paths or [],
                "previous_state": continuation["previous_state"],
                "next_turn_prompt": continuation["continuation_prompt"],
                "suggested_next_step": continuation["suggested_next_step"],
            }
        )
    return bundle


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


def build_playable_image_result(
    *,
    item: dict[str, Any],
    baseline: str,
    run_id: str,
    input_bundle: dict[str, Any],
    raw_output: dict[str, Any],
    image_paths: list[str],
    request_start_ts: float,
    first_playable_ts: float,
    finish_ts: float,
    success: bool,
    error: str | None = None,
    notes: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous_state = input_bundle.get("previous_state") or {}
    scene_setup = (
        f"The next-turn image continues the benchmark '{item.get('theme')}' after the chosen action and preserves the same world conflict."
    )
    player_state = (
        f"After the action '{input_bundle.get('player_action', DEFAULT_NEXT_TURN_ACTION)}', the protagonist remains in an advanceable state."
    )
    suggested_next_step = input_bundle.get("suggested_next_step") or "Use the continuation image to present the next actionable beat."
    playable_components = {
        "scene_setup": bool(scene_setup),
        "player_state": bool(player_state),
        "advanceable_next_step": bool(suggested_next_step),
        "interaction_continuity": bool(previous_state),
    }
    playable = success and sum(1 for value in playable_components.values() if value) >= 3
    payload = {
        "baseline_id": baseline,
        "benchmark_id": item.get("benchmark_id"),
        "run_id": run_id,
        "mode": "next_turn",
        "input_bundle": input_bundle,
        "raw_output": raw_output,
        "success": success,
        "latency_s": round(max(first_playable_ts - request_start_ts, 0.0), 3),
        "playable": playable,
        "playable_components": playable_components,
        "normalized_response": {
            "scene_setup": scene_setup,
            "player_state": player_state,
            "narrative_response": raw_output.get("narrative_response")
            or previous_state.get("narrative_response")
            or "Continuation image generated for the chosen action.",
            "candidate_actions": [],
            "suggested_next_step": suggested_next_step,
            "is_playable": playable,
            "request_start_ts": request_start_ts,
            "first_playable_ts": first_playable_ts,
            "finish_ts": finish_ts,
            "error": error,
            "notes": notes or [],
        },
        "image_artifacts": image_paths,
        "failure_reason": error,
        "resource_usage": {
            "gpu": get_gpu_info(),
            "hf_home": os.environ.get("HF_HOME"),
        },
        "notes": notes or [],
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


def summarize_results(
    run_dir: Path,
    baseline: str,
    results: list[dict[str, Any]],
    notes: str = "",
    *,
    mode: str = "first_turn",
) -> dict[str, Any]:
    latencies = [
        float(r["latency_s"])
        for r in results
        if r.get("status") == "success" and r.get("latency_s") is not None
    ]
    success = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "failed"]
    blocked = [r for r in results if r.get("status") == "blocked"]
    images_per_success = [len(r.get("image_paths") or []) for r in success]
    summary = {
        "baseline": baseline,
        "mode": mode,
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
    if mode == "next_turn":
        continuity_hits = sum(
            1
            for r in results
            if r.get("playable_components", {}).get("interaction_continuity")
        )
        summary["next_turn_time_mean_s"] = summary["mean_latency_s"]
        summary["next_turn_p95_s"] = summary["p95_latency_s"]
        summary["continuation_success_rate"] = summary["success_rate"]
        summary["interaction_continuity"] = round(continuity_hits / len(results), 4) if results else 0.0
    write_json(run_dir / "metrics.json", summary)
    write_json(run_dir / "summary.json", {"summary": summary, "results": results})
    write_summary_csv(run_dir / "summary.csv", summary)
    write_sample_index(run_dir / "sample_index.md", baseline, results)
    return summary


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    fields = [
        "baseline",
        "mode",
        "sample_size",
        "success_rate",
        "mean_latency_s",
        "p95_latency_s",
        "next_turn_time_mean_s",
        "next_turn_p95_s",
        "continuation_success_rate",
        "interaction_continuity",
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
        if result.get("mode"):
            lines.append(f"- mode: `{result.get('mode')}`")
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


def save_pil_images(images: Iterable[Any], sample_dir: Path, *, prefix: str = "image") -> list[str]:
    paths: list[str] = []
    for idx, image in enumerate(images, start=1):
        path = sample_dir / f"{prefix}_{idx:03d}.png"
        image.save(path)
        paths.append(str(path))
    return paths

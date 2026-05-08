from __future__ import annotations

import json
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_FILE = REPO_ROOT / "experiments" / "benchmark" / "dn_quality_benchmark_v1.json"


def load_benchmark_index() -> dict[str, dict[str, Any]]:
    payload = json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("benchmark_id"), str):
            index[item["benchmark_id"]] = item
    return index


def load_subset(path: str | Path) -> list[dict[str, Any]]:
    subset_path = Path(path)
    payload = json.loads(subset_path.read_text(encoding="utf-8"))
    benchmark_index = load_benchmark_index()
    rows: list[dict[str, Any]] = []
    for item in payload.get("items") or []:
        benchmark_id = item["benchmark_id"]
        merged = dict(benchmark_index[benchmark_id])
        merged["_subset_focus"] = item.get("focus")
        merged["_subset_name"] = payload.get("subset_name")
        rows.append(merged)
    return rows


def build_story_brief(item: dict[str, Any]) -> str:
    style = item.get("image_style") or {}
    style_name = style.get("type", "unspecified") if isinstance(style, dict) else str(style)
    must_have = "\n".join(f"- {entry}" for entry in item.get("must_have_constraints") or [])
    forbidden = "\n".join(f"- {entry}" for entry in item.get("forbidden_issues") or [])
    return (
        f"Theme: {item.get('theme', '')}\n"
        f"Genre: {item.get('expected_genre', '')}\n"
        f"Tone: {item.get('expected_tone', '')}\n"
        f"Visual style target: {style_name}\n"
        f"Must-have constraints:\n{must_have or '- None'}\n"
        f"Forbidden issues:\n{forbidden or '- None'}"
    )


def build_first_turn_prompt(item: dict[str, Any]) -> str:
    return (
        "You are producing a playable opening for an interactive narrative game. "
        "Return a grounded opening scene, the player state, and 2-4 concrete next actions.\n\n"
        + build_story_brief(item)
    )


def build_next_turn_prompt(item: dict[str, Any], previous_response: dict[str, Any], player_action: str) -> str:
    state_blob = json.dumps(previous_response, ensure_ascii=False, indent=2)
    return (
        "Continue the same interactive narrative. Keep the same world, player identity, and stakes. "
        "Respond to the player action with the next playable turn.\n\n"
        f"Benchmark brief:\n{build_story_brief(item)}\n\n"
        f"Previous playable response:\n{state_blob}\n\n"
        f"Player action: {player_action}"
    )


def extract_candidate_actions(raw_output: Any) -> list[str]:
    if isinstance(raw_output, dict):
        for key in ("candidate_actions", "actions", "options", "choices"):
            value = raw_output.get(key)
            if isinstance(value, list):
                return [str(entry).strip() for entry in value if str(entry).strip()]
        if isinstance(raw_output.get("suggested_next_step"), str):
            return [raw_output["suggested_next_step"].strip()]
    if isinstance(raw_output, str):
        lines = [line.strip("-* 0123456789.\t ") for line in raw_output.splitlines()]
        candidates = [line for line in lines if line and len(line) > 6]
        return candidates[:4]
    return []


def normalize_playable_response(
    *,
    baseline_id: str,
    benchmark_id: str,
    raw_output: Any,
    scene_setup: str = "",
    player_state: str = "",
    narrative_response: str = "",
    candidate_actions: list[str] | None = None,
    suggested_next_step: str = "",
    supports_next_turn: bool = False,
    request_start_ts: float | None = None,
    first_playable_ts: float | None = None,
    finish_ts: float | None = None,
    error: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    request_start_ts = request_start_ts if request_start_ts is not None else time.time()
    finish_ts = finish_ts if finish_ts is not None else time.time()
    first_playable_ts = first_playable_ts if first_playable_ts is not None else finish_ts
    candidate_actions = candidate_actions or extract_candidate_actions(raw_output)
    scene_text = (scene_setup or "").strip()
    player_text = (player_state or "").strip()
    narrative_text = (narrative_response or "").strip()
    if not narrative_text and isinstance(raw_output, str):
        narrative_text = raw_output.strip()
    if not scene_text and isinstance(raw_output, dict):
        for key in ("scene_setup", "scene", "opening_scene", "world_summary"):
            value = raw_output.get(key)
            if isinstance(value, str) and value.strip():
                scene_text = value.strip()
                break
    if not player_text and isinstance(raw_output, dict):
        for key in ("player_state", "protagonist_state", "character_state", "current_state"):
            value = raw_output.get(key)
            if isinstance(value, str) and value.strip():
                player_text = value.strip()
                break
    if not narrative_text and isinstance(raw_output, dict):
        for key in ("narrative_response", "response", "story", "text", "continuation"):
            value = raw_output.get(key)
            if isinstance(value, str) and value.strip():
                narrative_text = value.strip()
                break
    if not suggested_next_step and isinstance(raw_output, dict):
        value = raw_output.get("suggested_next_step")
        if isinstance(value, str):
            suggested_next_step = value.strip()

    components = {
        "scene_setup": bool(scene_text),
        "player_state": bool(player_text),
        "advanceable_next_step": bool(candidate_actions or suggested_next_step or narrative_text),
        "interaction_continuity": bool(supports_next_turn),
    }
    completeness = sum(1 for value in components.values() if value)
    is_playable = completeness >= 3 and not error
    return {
        "baseline_id": baseline_id,
        "benchmark_id": benchmark_id,
        "run_id": f"{baseline_id}_{benchmark_id}_{uuid.uuid4().hex[:8]}",
        "raw_output": raw_output,
        "success": bool(is_playable),
        "latency_s": round(max(first_playable_ts - request_start_ts, 0.0), 3),
        "playable": bool(is_playable),
        "playable_components": components,
        "normalized_response": {
            "scene_setup": scene_text,
            "player_state": player_text,
            "narrative_response": narrative_text,
            "candidate_actions": candidate_actions,
            "suggested_next_step": suggested_next_step,
            "is_playable": bool(is_playable),
            "request_start_ts": request_start_ts,
            "first_playable_ts": first_playable_ts,
            "finish_ts": finish_ts,
            "error": error,
            "notes": notes or [],
        },
    }


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    idx = (len(ordered) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return float(ordered[lo])
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def summarize_playable_runs(baseline_id: str, runs: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    latency_values = [float(run.get("latency_s", 0.0)) for run in runs if run.get("success")]
    completeness_values = [sum(1 for value in (run.get("playable_components") or {}).values() if value) for run in runs]
    continuity_hits = sum(1 for run in runs if (run.get("playable_components") or {}).get("interaction_continuity"))
    return {
        "baseline_id": baseline_id,
        "mode": mode,
        "sample_size": len(runs),
        "success_rate": round(sum(1 for run in runs if run.get("success")) / len(runs), 3) if runs else 0.0,
        "first_playable_time_mean_s": round(statistics.mean(latency_values), 3) if latency_values else None,
        "p95_latency_s": round(percentile(latency_values, 0.95) or 0.0, 3) if latency_values else None,
        "playable_output_completeness": round(statistics.mean(completeness_values), 3) if completeness_values else None,
        "interaction_continuity": round(continuity_hits / len(runs), 3) if runs else 0.0,
    }

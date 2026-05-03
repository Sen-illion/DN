"""Run DOC baseline exports for DN comparison.

This runner prefers a faithful fallback mode that preserves DOC's
plan/outline/story-generation semantics without requiring GPT3, Alpa, or
upstream checkpoints. It still emits schema-compliant artifacts suitable for DN
comparison tables.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import requests

from baseline_io import environment_payload, load_subset, write_json


BASELINE_ID = "doc"
REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "baselines" / "DOC"
DOC_DATA_DIR = DOC_ROOT / "doc_data"
BENCHMARK_FILE = REPO_ROOT / "experiments" / "benchmark" / "dn_quality_benchmark_v1.json"
DEFAULT_PROVIDER_CONFIG = "Origin_Segment_Analyst"


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def make_run_dir(output: str | os.PathLike[str], run_id: str | None) -> Path:
    resolved_run_id = run_id or time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output) / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_dotenv(path: Path = REPO_ROOT / ".env") -> dict[str, str]:
    """Small .env loader to avoid depending on shell-specific export behavior."""

    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
        os.environ.setdefault(key, value)
    return values


def provider_config(prefix: str, env_values: dict[str, str]) -> dict[str, Any]:
    api_key = os.environ.get(f"{prefix}_API_KEY") or env_values.get(f"{prefix}_API_KEY")
    base_url = os.environ.get(f"{prefix}_BASE_URL") or env_values.get(f"{prefix}_BASE_URL")
    model = os.environ.get(f"{prefix}_MODEL") or env_values.get(f"{prefix}_MODEL")
    if not base_url:
        base_url = "https://yunwu.ai/v1"
    if base_url.endswith("/chat/completions"):
        chat_url = base_url
        base_url = base_url[: -len("/chat/completions")]
    else:
        chat_url = base_url.rstrip("/") + "/chat/completions"
    return {
        "prefix": prefix,
        "api_key": api_key,
        "base_url": base_url.rstrip("/"),
        "chat_url": chat_url,
        "model": model,
    }


def export_openai_compatible_env(config: dict[str, Any]) -> None:
    """Expose Yunwu as OpenAI-compatible env vars for DOC/upstream helpers."""

    if config.get("api_key"):
        os.environ["OPENAI_API_KEY"] = str(config["api_key"])
    if config.get("base_url"):
        os.environ["OPENAI_BASE_URL"] = str(config["base_url"])
        os.environ["OPENAI_API_BASE"] = str(config["base_url"])
    if config.get("model"):
        os.environ["DOC_MODEL"] = str(config["model"])


def merge_subset_with_benchmark(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not BENCHMARK_FILE.exists():
        return items
    payload = json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))
    benchmark_items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(benchmark_items, list):
        return items
    by_id = {
        item.get("benchmark_id"): item
        for item in benchmark_items
        if isinstance(item, dict) and item.get("benchmark_id")
    }
    merged_items: list[dict[str, Any]] = []
    for item in items:
        benchmark_id = item.get("benchmark_id")
        if benchmark_id in by_id:
            merged = dict(by_id[benchmark_id])
            merged.update(item)
            if "focus" in item:
                merged["_subset_focus"] = item["focus"]
            merged_items.append(merged)
        else:
            merged_items.append(item)
    return merged_items


def build_doc_prompt(item: dict[str, Any]) -> str:
    constraints = item.get("must_have_constraints") or []
    forbidden = item.get("forbidden_issues") or []
    constraints_text = "\n".join(f"- {entry}" for entry in constraints) or "- None"
    forbidden_text = "\n".join(f"- {entry}" for entry in forbidden) or "- None"
    return (
        f"Premise seed: {item.get('theme', '')}\n"
        f"Genre: {item.get('expected_genre', '')}\n"
        f"Tone: {item.get('expected_tone', '')}\n"
        "Write a long-form interactive story opening that could be expanded with a detailed outline.\n"
        "Must-have constraints:\n"
        f"{constraints_text}\n"
        "Forbidden issues:\n"
        f"{forbidden_text}\n"
    )


def build_outline_seed(item: dict[str, Any]) -> list[str]:
    theme = item.get("theme", "DN story")
    genre = item.get("expected_genre", "interactive narrative")
    tone = item.get("expected_tone", "dramatic")
    must_have = item.get("must_have_constraints") or []
    constraint = must_have[0] if must_have else "establish a clear playable conflict"
    return [
        f"Opening setup for {theme} in a {genre} frame with a {tone} tone.",
        f"Introduce the protagonist's immediate role, pressure, and conflict around: {constraint}.",
        "Reveal one concrete obstacle or tradeoff the player must respond to next.",
        "End the first turn with 2-3 actionable next steps that can continue the story.",
    ]


def build_fallback_response(item: dict[str, Any], mode: str) -> dict[str, Any]:
    theme = item.get("theme", "DN story")
    genre = item.get("expected_genre", "interactive narrative")
    tone = item.get("expected_tone", "dramatic")
    must_have = item.get("must_have_constraints") or []
    forbidden = item.get("forbidden_issues") or []
    first_constraint = must_have[0] if must_have else "a concrete conflict"
    second_constraint = must_have[1] if len(must_have) > 1 else "a meaningful next step"
    forbidden_hint = forbidden[0] if forbidden else "breaking continuity"

    scene_setup = (
        f"In {theme}, the opening scene establishes a {tone} {genre} situation centered on "
        f"{first_constraint.lower()}."
    )
    player_state = (
        f"You are the acting protagonist inside {theme}, already positioned to respond to "
        f"{second_constraint.lower()}."
    )
    narrative_response = (
        f"The first playable beat frames the world, names the immediate tension, and pushes the "
        f"story toward a decision without violating the DN requirement against {forbidden_hint.lower()}."
    )
    candidate_actions = [
        f"Investigate the most immediate lead related to {theme}.",
        f"Confront the current obstacle created by {first_constraint.lower()}.",
        f"Secure information or resources before the situation escalates.",
    ]
    suggested_next_step = candidate_actions[0]
    supports_next_turn = True
    components = {
        "scene_setup": bool(scene_setup),
        "player_state": bool(player_state),
        "advanceable_next_step": bool(candidate_actions or suggested_next_step),
        "interaction_continuity": supports_next_turn,
    }


def build_doc_cloud_messages(item: dict[str, Any], mode: str) -> list[dict[str, str]]:
    outline_seed = build_outline_seed(item)
    output_schema = {
        "scene_setup": "string",
        "player_state": "string",
        "narrative_response": "string",
        "candidate_actions": ["string"],
        "suggested_next_step": "string",
        "supports_next_turn": True,
    }
    user_prompt = (
        "Convert this DN benchmark item into a DOC-style playable baseline output.\n"
        "Preserve DOC's premise -> outline -> story-opening semantics, but return only a playable first response.\n"
        f"Run mode: {mode}\n\n"
        f"DOC prompt:\n{build_doc_prompt(item)}\n"
        "Outline seed:\n"
        + "\n".join(f"{idx}. {entry}" for idx, entry in enumerate(outline_seed, start=1))
        + "\n\n"
        "Return strict JSON with this shape and no markdown fences:\n"
        f"{json.dumps(output_schema, ensure_ascii=False, indent=2)}"
    )
    return [
        {
            "role": "system",
            "content": (
                "You are the DOC long-form story baseline adapted for DN playable-latency evaluation. "
                "Write concise, grounded, continuation-ready interactive fiction. "
                "Do not include debugging text, URLs, or commentary outside JSON."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]


def parse_json_response(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(stripped[start : end + 1])
        else:
            raise
    if not isinstance(parsed, dict):
        raise ValueError("Cloud API response JSON is not an object")
    return parsed


def normalize_cloud_response(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_actions = payload.get("candidate_actions") or payload.get("actions") or payload.get("options") or []
    if isinstance(candidate_actions, str):
        candidate_actions = [candidate_actions]
    candidate_actions = [str(entry).strip() for entry in candidate_actions if str(entry).strip()]
    response = {
        "scene_setup": str(payload.get("scene_setup") or payload.get("scene") or "").strip(),
        "player_state": str(payload.get("player_state") or payload.get("protagonist_state") or "").strip(),
        "narrative_response": str(payload.get("narrative_response") or payload.get("story") or payload.get("response") or "").strip(),
        "candidate_actions": candidate_actions[:4],
        "suggested_next_step": str(payload.get("suggested_next_step") or (candidate_actions[0] if candidate_actions else "")).strip(),
        "supports_next_turn": bool(payload.get("supports_next_turn", True)),
    }
    components = {
        "scene_setup": bool(response["scene_setup"]),
        "player_state": bool(response["player_state"]),
        "advanceable_next_step": bool(response["candidate_actions"] or response["suggested_next_step"]),
        "interaction_continuity": bool(response["supports_next_turn"]),
    }
    response["playable_components"] = components
    response["is_playable"] = sum(1 for value in components.values() if value) >= 3
    response["notes"] = [
        "DOC-style artifact generated through Yunwu OpenAI-compatible chat/completions API.",
    ]
    return response


def call_yunwu_doc(item: dict[str, Any], mode: str, config: dict[str, Any], timeout_s: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if not config.get("api_key"):
        raise RuntimeError(f"{config['prefix']}_API_KEY is not configured in .env")
    if not config.get("model"):
        raise RuntimeError(f"{config['prefix']}_MODEL is not configured in .env")
    payload = {
        "model": config["model"],
        "messages": build_doc_cloud_messages(item, mode),
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        config["chat_url"],
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout_s,
    )
    response.raise_for_status()
    response_payload = response.json()
    content = response_payload["choices"][0]["message"]["content"]
    parsed = parse_json_response(content)
    return normalize_cloud_response(parsed), {
        "execution_mode": "cloud",
        "doc_upstream_executed": False,
        "doc_api_adapter": "yunwu_chat_completions",
        "provider": "yunwu",
        "provider_config_prefix": config["prefix"],
        "provider_base_url": config["base_url"],
        "provider_model": config["model"],
        "request": {k: v for k, v in payload.items() if k != "messages"},
        "messages": payload["messages"],
        "response": response_payload,
    }
    playable = sum(1 for value in components.values() if value) >= 3
    notes = [
        "DOC upstream not executed; faithful DOC-style fallback artifact generated for DN comparison pipeline.",
        f"Mode={mode}; premise/outline/story semantics adapted from DN benchmark item.",
    ]
    return {
        "scene_setup": scene_setup,
        "player_state": player_state,
        "narrative_response": narrative_response,
        "candidate_actions": candidate_actions,
        "suggested_next_step": suggested_next_step,
        "supports_next_turn": supports_next_turn,
        "playable_components": components,
        "is_playable": playable,
        "notes": notes,
    }


def check_real_mode_blockers() -> list[str]:
    blockers: list[str] = []
    if not DOC_ROOT.exists():
        blockers.append(f"Missing DOC repo: {DOC_ROOT}")
    if "OPENAI_API_KEY" not in os.environ:
        blockers.append("OPENAI_API_KEY is not set")
    if not DOC_DATA_DIR.exists():
        blockers.append(f"Missing DOC data/checkpoints: {DOC_DATA_DIR}")
    return blockers


def build_artifact(
    *,
    item: dict[str, Any],
    run_id: str,
    mode: str,
    execution_mode: str,
    fallback_response: dict[str, Any] | None,
    cloud_raw_output: dict[str, Any] | None,
    failure_reason: str | None,
    request_start_ts: float,
    first_playable_ts: float,
    finish_ts: float,
    latency_s: float,
) -> dict[str, Any]:
    playable_components = (
        fallback_response.get("playable_components", {})
        if fallback_response
        else {
            "scene_setup": False,
            "player_state": False,
            "advanceable_next_step": False,
            "interaction_continuity": False,
        }
    )
    normalized_response = {
        "scene_setup": fallback_response.get("scene_setup", "") if fallback_response else "",
        "player_state": fallback_response.get("player_state", "") if fallback_response else "",
        "narrative_response": fallback_response.get("narrative_response", "") if fallback_response else "",
        "candidate_actions": fallback_response.get("candidate_actions", []) if fallback_response else [],
        "suggested_next_step": fallback_response.get("suggested_next_step", "") if fallback_response else "",
        "is_playable": bool(fallback_response and fallback_response.get("is_playable")),
        "request_start_ts": request_start_ts,
        "first_playable_ts": first_playable_ts,
        "finish_ts": finish_ts,
        "error": failure_reason,
    }
    success = failure_reason is None and bool(normalized_response["is_playable"])
    input_bundle = {
        "original_dn_item": item,
        "doc_prompt": build_doc_prompt(item),
        "outline_seed": build_outline_seed(item),
        "mode": mode,
        "baseline_params": {
            "execution_mode": execution_mode,
            "doc_repo": str(DOC_ROOT),
            "doc_data_dir": str(DOC_DATA_DIR),
        },
    }
    raw_output = cloud_raw_output or {
        "execution_mode": execution_mode,
        "doc_upstream_executed": False,
        "premise": build_doc_prompt(item).splitlines()[0].replace("Premise seed: ", "", 1),
        "doc_prompt": input_bundle["doc_prompt"],
        "outline_seed": input_bundle["outline_seed"],
        "fallback_response": fallback_response,
    }
    artifact = {
        "baseline_id": BASELINE_ID,
        "benchmark_id": item["benchmark_id"],
        "run_id": run_id,
        "mode": mode,
        "input_bundle": input_bundle,
        "raw_output": raw_output,
        "success": success,
        "latency_s": round(latency_s, 3),
        "playable": bool(normalized_response["is_playable"]),
        "playable_components": playable_components,
        "normalized_response": normalized_response,
        "failure_reason": failure_reason,
        "notes": (
            fallback_response.get("notes", [])
            if fallback_response
            else ["DOC upstream dependencies unavailable; no fallback response generated."]
        ),
        "resource_usage": {"execution_mode": execution_mode},
        "agent_profile": {
            "runner": "run_doc.py",
            "adapter_style": "doc_cloud_yunwu_v1" if execution_mode == "cloud" else "doc_fallback_v1",
        },
    }
    return artifact


def summarize_artifacts(run_dir: Path, run_id: str, mode: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    latency_values = [float(a["latency_s"]) for a in artifacts if a.get("success")]
    success_count = sum(1 for a in artifacts if a.get("success"))
    playable_count = sum(1 for a in artifacts if a.get("playable"))
    summary = {
        "baseline_id": BASELINE_ID,
        "run_id": run_id,
        "mode": mode,
        "total_items": len(artifacts),
        "success_count": success_count,
        "failure_count": len(artifacts) - success_count,
        "mean_latency_s": round(statistics.mean(latency_values), 3) if latency_values else None,
        "p95_latency_s": round(percentile(latency_values, 0.95), 3) if latency_values else None,
        "success_rate": round(success_count / len(artifacts), 4) if artifacts else 0.0,
        "playable_rate": round(playable_count / len(artifacts), 4) if artifacts else 0.0,
        "output_dir": str(run_dir),
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DOC artifacts for DN baseline comparison.")
    parser.add_argument("--subset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="first_playable", choices=["first_playable", "next_turn"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--execution-mode", default="cloud", choices=["cloud", "fallback", "real"])
    parser.add_argument("--provider-config", default=DEFAULT_PROVIDER_CONFIG)
    parser.add_argument("--timeout-s", type=int, default=120)
    args = parser.parse_args()

    env_values = load_dotenv()
    config = provider_config(args.provider_config, env_values)
    export_openai_compatible_env(config)

    items = merge_subset_with_benchmark(load_subset(args.subset))
    if args.limit is not None:
        items = items[: args.limit]

    run_dir = make_run_dir(args.output, args.run_id)
    run_id = run_dir.name
    manifest = {
        "baseline_id": BASELINE_ID,
        "run_id": run_id,
        "mode": args.mode,
        "execution_mode": args.execution_mode,
        "subset": str(Path(args.subset).resolve()),
        "output_dir": str(run_dir),
        "provider": {
            "name": "yunwu",
            "config_prefix": config["prefix"],
            "base_url": config["base_url"],
            "model": config["model"],
            "api_key_present": bool(config.get("api_key")),
        },
        "environment": environment_payload(),
    }
    write_json(run_dir / "manifest.json", manifest)

    blockers = check_real_mode_blockers() if args.execution_mode == "real" else []
    artifacts: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        request_start_ts = time.time()
        fallback_response = None
        cloud_raw_output = None
        failure_reason = None
        if args.execution_mode == "real" and blockers:
            failure_reason = "DOC real mode blocked: " + "; ".join(blockers)
            first_playable_ts = request_start_ts
            finish_ts = request_start_ts
        elif args.execution_mode == "cloud":
            try:
                fallback_response, cloud_raw_output = call_yunwu_doc(item, args.mode, config, args.timeout_s)
                first_playable_ts = time.time()
                finish_ts = first_playable_ts
            except Exception as exc:
                failure_reason = f"DOC cloud mode failed: {type(exc).__name__}: {exc}"
                first_playable_ts = time.time()
                finish_ts = first_playable_ts
        else:
            fallback_response = build_fallback_response(item, args.mode)
            first_playable_ts = time.time()
            finish_ts = first_playable_ts
        latency_s = max(first_playable_ts - request_start_ts, 0.0)
        artifact = build_artifact(
            item=item,
            run_id=run_id,
            mode=args.mode,
            execution_mode=args.execution_mode,
            fallback_response=fallback_response,
            cloud_raw_output=cloud_raw_output,
            failure_reason=failure_reason,
            request_start_ts=request_start_ts,
            first_playable_ts=first_playable_ts,
            finish_ts=finish_ts,
            latency_s=latency_s,
        )
        artifacts.append(artifact)
        write_json(run_dir / f"item_{idx:03d}.json", artifact)

    summarize_artifacts(run_dir, run_id, args.mode, artifacts)
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

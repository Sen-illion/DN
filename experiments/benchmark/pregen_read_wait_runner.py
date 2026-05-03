from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_FILE = REPO_ROOT / "experiments" / "benchmark" / "dn_quality_benchmark_v1.json"
OUTPUT_DIR = REPO_ROOT / "experiments" / "benchmark" / "standard_runs"
PROVIDER_EVENTS_FILE = REPO_ROOT / "logs" / "provider_events.jsonl"
DEFAULT_BASE_URL = "http://127.0.0.1:5001"
STRICT_PROFILES = {"fullready_strict", "fullready_pregen60"}


def load_benchmark(limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
    payload = json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    picked = [item for item in items if isinstance(item, dict)]
    if offset:
        picked = picked[offset:]
    if limit is not None:
        picked = picked[:limit]
    return picked


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


def summarize_numeric(values: list[float]) -> dict[str, Any]:
    cleaned = [float(v) for v in values if isinstance(v, (int, float))]
    if not cleaned:
        return {"count": 0}
    return {
        "count": len(cleaned),
        "min": round(min(cleaned), 3),
        "max": round(max(cleaned), 3),
        "mean": round(statistics.mean(cleaned), 3),
        "median": round(statistics.median(cleaned), 3),
        "p95": round(percentile(cleaned, 0.95) or 0.0, 3),
    }


def safe_json(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"_raw": data}
    except Exception:
        return {"_raw_text": resp.text[:4000]}


def provider_events_in_window(start_ts: float, end_ts: float) -> list[dict[str, Any]]:
    if not PROVIDER_EVENTS_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    with PROVIDER_EVENTS_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            ts = item.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            if start_ts <= float(ts) <= end_ts:
                rows.append(item)
    return rows


def summarize_provider_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    queue_vals = [float(e["queue_wait_ms"]) for e in events if isinstance(e.get("queue_wait_ms"), (int, float))]
    latency_vals = [float(e["latency_ms"]) for e in events if isinstance(e.get("latency_ms"), (int, float))]
    llm_success = sum(1 for e in events if e.get("kind") == "llm" and e.get("status") == "success")
    image_success = sum(1 for e in events if e.get("kind") == "image" and e.get("status") == "success")
    request_thread_events = sum(
        1
        for e in events
        if isinstance(e.get("thread"), str) and "process_request_thread" in str(e.get("thread"))
    )
    provider_429_count = sum(
        1
        for e in events
        if (e.get("status_code") == 429)
        or (e.get("reason") in {"http_429", "http_429_upstream_saturated"})
        or (e.get("status") == "shared_backoff_set" and str(e.get("reason", "")).startswith("http_429"))
    )
    provider_timeout_count = sum(
        1
        for e in events
        if e.get("reason") in {"timeout", "timeout_exception"} or "timeout" in str(e.get("status") or "").lower()
    )
    shared_backoff_wait_ms = sum(
        int(e["shared_backoff_wait_ms"])
        for e in events
        if isinstance(e.get("shared_backoff_wait_ms"), (int, float))
    )
    retry_heavy_event_count = sum(
        1 for e in events if isinstance(e.get("attempt"), (int, float)) and int(e.get("attempt", 0)) >= 3
    )
    main_character_event_count = sum(1 for e in events if e.get("request_type") == "main_character")
    scene_image_event_count = sum(1 for e in events if e.get("request_type") == "scene_image")
    return {
        "event_count": len(events),
        "queue_wait_ms": summarize_numeric(queue_vals),
        "latency_ms": summarize_numeric(latency_vals),
        "llm_success_count": llm_success,
        "image_success_count": image_success,
        "request_thread_event_count": request_thread_events,
        "provider_429_count": provider_429_count,
        "provider_timeout_count": provider_timeout_count,
        "shared_backoff_wait_ms_total": shared_backoff_wait_ms,
        "retry_heavy_event_count": retry_heavy_event_count,
        "main_character_event_count": main_character_event_count,
        "scene_image_event_count": scene_image_event_count,
    }


def benchmark_flags(profile: str, read_wait_s: float) -> dict[str, Any]:
    return {
        "_benchmark_profile": profile,
        "_benchmark_measurement": "fullready_nextturn",
        "_benchmark_read_wait_s": read_wait_s,
    }


def merge_benchmark_flags(state: dict[str, Any] | None, profile: str, read_wait_s: float) -> dict[str, Any]:
    payload = json.loads(json.dumps(state or {}, ensure_ascii=False))
    payload.update(benchmark_flags(profile, read_wait_s))
    return payload


def flatten_provider_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    block = summary or {}
    return {
        "provider_429_count": int(block.get("provider_429_count", 0) or 0),
        "provider_timeout_count": int(block.get("provider_timeout_count", 0) or 0),
        "provider_retry_heavy_count": int(block.get("retry_heavy_event_count", 0) or 0),
        "provider_backoff_wait_ms_total": int(block.get("shared_backoff_wait_ms_total", 0) or 0),
        "main_character_event_count": int(block.get("main_character_event_count", 0) or 0),
        "scene_image_event_count": int(block.get("scene_image_event_count", 0) or 0),
    }


def compute_long_tail_attribution(run: dict[str, Any]) -> dict[str, Any]:
    second_click = run.get("second_click") or {}
    second_summary = flatten_provider_summary(second_click.get("provider_events"))
    for attempt in second_click.get("attempts") or []:
        flat = flatten_provider_summary(attempt.get("provider_events"))
        for key, value in flat.items():
            second_summary[key] += value
    probe = (run.get("full_ready") or {}).get("image_probe") or {}
    attempts = probe.get("attempts") or []
    image_summary = {
        "provider_429_count": 0,
        "provider_timeout_count": 0,
        "provider_retry_heavy_count": 0,
        "provider_backoff_wait_ms_total": 0,
        "main_character_event_count": 0,
        "scene_image_event_count": 0,
    }
    for attempt in attempts:
        flat = flatten_provider_summary(attempt.get("provider_events"))
        for key, value in flat.items():
            image_summary[key] += value

    combined = {key: second_summary.get(key, 0) + image_summary.get(key, 0) for key in image_summary}
    attempt_count = int(probe.get("attempt_count", 0) or 0)
    combined["image_probe_attempt_count"] = attempt_count
    combined["main_character_contention_suspected"] = bool(
        combined["main_character_event_count"] > 0 and (combined["provider_429_count"] > 0 or attempt_count >= 3)
    )
    return combined


def timed_post(
    session: requests.Session,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout_s: int = 1800,
) -> dict[str, Any]:
    start_wall = time.time()
    start_perf = time.perf_counter()
    try:
        resp = session.post(f"{base_url}{path}", json=payload, timeout=timeout_s)
        elapsed = time.perf_counter() - start_perf
        end_wall = time.time()
        return {
            "http_status": resp.status_code,
            "elapsed_s": round(elapsed, 3),
            "response_json": safe_json(resp),
            "request_payload": payload,
            "start_ts": start_wall,
            "end_ts": end_wall,
            "provider_events": summarize_provider_events(provider_events_in_window(start_wall, end_wall + 0.5)),
        }
    except requests.exceptions.Timeout as exc:
        end_wall = time.time()
        elapsed = time.perf_counter() - start_perf
        return {
            "http_status": None,
            "elapsed_s": round(elapsed, 3),
            "response_json": {"status": "timeout", "message": str(exc)},
            "request_payload": payload,
            "start_ts": start_wall,
            "end_ts": end_wall,
            "provider_events": summarize_provider_events(provider_events_in_window(start_wall, end_wall + 0.5)),
            "request_error": "timeout",
        }


def generate_worldview(
    session: requests.Session,
    base_url: str,
    item: dict[str, Any],
    *,
    profile: str,
    read_wait_s: float,
) -> dict[str, Any]:
    payload = {
        "gameTheme": item["theme"],
        "protagonistAttr": {},
        "difficulty": "normal",
        "toneKey": "normal_ending",
        "imageStyle": item["image_style"],
    }
    payload.update(benchmark_flags(profile, read_wait_s))
    run = timed_post(session, base_url, "/generate-worldview", payload)
    data = run["response_json"]
    global_state = data.get("globalState") if isinstance(data.get("globalState"), dict) else {}
    run.update(
        {
            "status": data.get("status"),
            "game_id": data.get("gameId") or data.get("game_id") or global_state.get("game_id"),
        }
    )
    return run


def pick_option(option_data: dict[str, Any], fallback_text: str) -> tuple[int, str]:
    next_options = option_data.get("next_options") or []
    if isinstance(next_options, list) and next_options:
        return 0, str(next_options[0])
    return 0, fallback_text


def apply_flow_update(global_state: dict[str, Any], option_data: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(global_state or {}, ensure_ascii=False))
    flow = updated.setdefault("flow_worldline", {})
    flow_update = option_data.get("flow_update") or {}
    if isinstance(flow_update, dict):
        if flow_update.get("quest_progress"):
            flow["quest_progress"] = flow_update["quest_progress"]
        if isinstance(flow_update.get("chapter_conflict_solved"), bool):
            flow["chapter_conflict_solved"] = flow_update["chapter_conflict_solved"]
        for key in ("characters", "environment", "current_chapter"):
            if key in flow_update and flow_update[key] is not None:
                flow[key] = flow_update[key]
    current_progress = flow.get("chapter_progress")
    if isinstance(current_progress, (int, float)):
        flow["chapter_progress"] = round(min(95.0, float(current_progress) + 2.0), 1)
    else:
        flow["chapter_progress"] = 2.0
    return updated


def is_placeholder_option_data(option_data: dict[str, Any]) -> bool:
    scene = str(option_data.get("scene") or "").strip()
    next_options = option_data.get("next_options") or []
    generic_option_sets = [
        ["继续前进", "查看周围环境"],
        ["继续前进", "查看当前状态", "返回上一步", "探索周围环境"],
    ]
    if not scene:
        return True
    if "当前内容生成耗时较长" in scene:
        return True
    if scene.startswith("你选择了：继续前进。"):
        return True
    if len(scene) < 80:
        return True
    if next_options in generic_option_sets:
        return True
    return False


def fetch_story_option_with_retry(
    session: requests.Session,
    base_url: str,
    payload: dict[str, Any],
    retries: int = 5,
    wait_s: float = 5.0,
    timeout_s: int = 1800,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last = timed_post(session, base_url, "/generate-option", payload, timeout_s=timeout_s)
    attempts.append(json.loads(json.dumps(last, ensure_ascii=False)))
    first_start_ts = float(last.get("start_ts") or time.time())
    data = last.get("response_json") or {}
    option_data = data.get("optionData") or {}
    attempt = 0
    while attempt < retries and data.get("status") == "success" and is_placeholder_option_data(option_data):
        attempt += 1
        time.sleep(wait_s)
        last = timed_post(session, base_url, "/generate-option", payload, timeout_s=timeout_s)
        attempts.append(json.loads(json.dumps(last, ensure_ascii=False)))
        data = last.get("response_json") or {}
        option_data = data.get("optionData") or {}
    last["attempts"] = attempts
    last["attempt_count"] = len(attempts)
    last["request_elapsed_s"] = last.get("elapsed_s")
    last["start_ts"] = first_start_ts
    last["elapsed_s"] = round(float(last.get("end_ts") or first_start_ts) - first_start_ts, 3)
    last["retry_count"] = attempt
    last["is_placeholder"] = is_placeholder_option_data(option_data) if data.get("status") == "success" else False
    return last


def classify_second_click(second_click: dict[str, Any]) -> str:
    events = second_click.get("provider_events") or {}
    if events.get("llm_success_count", 0) == 0 and events.get("request_thread_event_count", 0) == 0:
        return "likely_hit"
    return "likely_miss_or_partial"


def extract_benchmark_diagnostics(response_json: dict[str, Any] | None) -> dict[str, Any]:
    block = (response_json or {}).get("benchmark_diagnostics") or {}
    return block if isinstance(block, dict) else {}


def infer_image_style(item: dict[str, Any]) -> str:
    image_style = item.get("image_style")
    if isinstance(image_style, dict):
        return str(image_style.get("type") or image_style.get("style") or "default")
    if isinstance(image_style, str) and image_style.strip():
        return image_style.strip()
    return "default"


def build_scene_image_payload(
    item: dict[str, Any],
    scene_description: str,
    global_state: dict[str, Any],
    current_scene_id: str | None,
    previous_scene_image: dict[str, Any] | None,
    previous_scene_text: str,
) -> dict[str, Any]:
    payload_global_state = json.loads(json.dumps(global_state or {}, ensure_ascii=False))
    payload_global_state["_visual_context"] = {
        "sceneId": current_scene_id,
        "previousSceneImage": previous_scene_image,
        "previousSceneText": previous_scene_text or "",
    }
    return {
        "sceneDescription": scene_description,
        "globalState": payload_global_state,
        "style": infer_image_style(item),
    }


def wait_for_scene_image(
    session: requests.Session,
    base_url: str,
    payload: dict[str, Any],
    start_ts: float,
    timeout_s: float,
    poll_interval_s: float,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    deadline = time.time() + timeout_s
    while True:
        remaining = max(1.0, deadline - time.time())
        probe = timed_post(
            session,
            base_url,
            "/generate-scene-image",
            payload,
            timeout_s=max(1, int(min(timeout_s, remaining))),
        )
        attempts.append(probe)
        response_json = probe.get("response_json") or {}
        image = response_json.get("image") or {}
        status = response_json.get("status")
        if probe.get("http_status") == 200 and status == "success" and image.get("url"):
            return {
                "status": "success",
                "source": "generate-scene-image",
                "attempt_count": len(attempts),
                "attempts": attempts,
                "image_ready_ts": probe["end_ts"],
                "image_ready_elapsed_s": round(probe["end_ts"] - start_ts, 3),
                "image": image,
                "request_key": response_json.get("requestKey"),
            }
        if time.time() >= deadline:
            return {
                "status": "timeout",
                "source": "generate-scene-image",
                "attempt_count": len(attempts),
                "attempts": attempts,
                "error": response_json.get("message") or "scene image timeout",
                "request_key": response_json.get("requestKey"),
            }
        time.sleep(poll_interval_s)


def maybe_collect_full_ready(
    session: requests.Session,
    base_url: str,
    item: dict[str, Any],
    updated_global_state: dict[str, Any],
    second_click: dict[str, Any],
    current_scene_id: str | None,
    previous_scene_image: dict[str, Any] | None,
    previous_scene_text: str,
    image_timeout_s: float,
    image_poll_interval_s: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "text_ready_ts": second_click.get("end_ts"),
        "text_ready_elapsed_s": second_click.get("elapsed_s"),
        "image_ready_ts": None,
        "image_ready_elapsed_s": None,
        "full_ready_ts": None,
        "full_ready_elapsed_s": None,
        "image_probe": None,
        "ready_mode": "blocked",
    }

    if second_click.get("status") != "success":
        result["error"] = "second_click_not_success"
        return result

    option_data = (second_click.get("response_json") or {}).get("optionData") or {}
    scene_text = str(option_data.get("scene") or "").strip()
    if not scene_text:
        result["error"] = "second_click_missing_scene"
        return result

    direct_image = option_data.get("scene_image") or {}
    if direct_image.get("url"):
        result["image_ready_ts"] = second_click.get("end_ts")
        result["image_ready_elapsed_s"] = second_click.get("elapsed_s")
        result["full_ready_ts"] = second_click.get("end_ts")
        result["full_ready_elapsed_s"] = second_click.get("elapsed_s")
        result["ready_mode"] = "direct_in_generate_option"
        result["image_probe"] = {
            "status": "success",
            "source": "generate-option",
            "image": direct_image,
            "attempt_count": 0,
        }
        return result

    payload = build_scene_image_payload(
        item=item,
        scene_description=scene_text,
        global_state=updated_global_state,
        current_scene_id=current_scene_id,
        previous_scene_image=previous_scene_image,
        previous_scene_text=previous_scene_text,
    )
    probe = wait_for_scene_image(
        session=session,
        base_url=base_url,
        payload=payload,
        start_ts=float(second_click["start_ts"]),
        timeout_s=image_timeout_s,
        poll_interval_s=image_poll_interval_s,
    )
    result["image_probe"] = probe
    if probe.get("status") == "success":
        result["image_ready_ts"] = probe.get("image_ready_ts")
        result["image_ready_elapsed_s"] = probe.get("image_ready_elapsed_s")
        result["full_ready_ts"] = max(float(second_click["end_ts"]), float(probe["image_ready_ts"]))
        result["full_ready_elapsed_s"] = round(result["full_ready_ts"] - float(second_click["start_ts"]), 3)
        result["ready_mode"] = "async_generate_scene_image"
    else:
        result["error"] = probe.get("error") or probe.get("status") or "scene_image_probe_failed"
    return result


def compute_transport_success(run: dict[str, Any], full_ready: bool) -> bool:
    if full_ready:
        full = run.get("full_ready") or {}
        return isinstance(full.get("full_ready_elapsed_s"), (int, float))
    second = run.get("second_click") or {}
    return second.get("status") == "success" and bool(second.get("has_scene"))


def compute_strict_success(run: dict[str, Any], full_ready: bool) -> bool:
    if not compute_transport_success(run, full_ready):
        return False
    return not bool((run.get("second_click") or {}).get("is_placeholder"))


def classify_cache_path(run: dict[str, Any]) -> str:
    first = run.get("first_click") or {}
    second = run.get("second_click") or {}
    full = run.get("full_ready") or {}
    if first.get("request_error") == "timeout" or first.get("status") == "timeout":
        return "first_click_timeout"
    if second.get("request_error") == "timeout" or second.get("status") == "timeout":
        return "second_click_timeout"
    if second.get("status") == "success" and second.get("is_placeholder") and not second.get("has_image"):
        return "placeholder_no_image"
    if second.get("inferred_cache_result") == "likely_hit" and full.get("ready_mode") == "direct_in_generate_option":
        return "likely_hit_direct_image"
    if full.get("ready_mode") == "direct_in_generate_option" and second.get("is_placeholder"):
        return "direct_placeholder"
    if full.get("ready_mode") == "direct_in_generate_option":
        return "direct_real_scene"
    if full.get("ready_mode") == "async_generate_scene_image" and second.get("is_placeholder"):
        return "async_after_placeholder"
    if full.get("ready_mode") == "async_generate_scene_image":
        return "async_after_real_scene"
    if second.get("status") == "success" and second.get("has_scene") and not second.get("has_image"):
        return "scene_without_image"
    return "other"


def classify_failure_bucket(run: dict[str, Any], full_ready: bool) -> str | None:
    if compute_strict_success(run, full_ready):
        return None
    first = run.get("first_click") or {}
    second = run.get("second_click") or {}
    full = run.get("full_ready") or {}
    if first.get("request_error") == "timeout" or first.get("status") == "timeout":
        return "first_click_timeout"
    if second.get("request_error") == "timeout" or second.get("status") == "timeout":
        return "second_click_timeout"
    if second.get("status") == "success" and second.get("is_placeholder") and not second.get("has_image"):
        return "placeholder_no_image"
    if ((full.get("image_probe") or {}).get("status") == "timeout") or full.get("error") == "scene_image_probe_failed":
        return "image_probe_timeout"
    if second.get("status") == "success" and second.get("is_placeholder"):
        return "placeholder_strict_fail"
    return "other"


def compute_first_click_setup_success(first_click: dict[str, Any]) -> bool:
    if not isinstance(first_click, dict):
        return False
    if first_click.get("status") != "success":
        return False
    if not first_click.get("has_scene"):
        return False
    if first_click.get("is_placeholder"):
        return False
    option_data = (first_click.get("response_json") or {}).get("optionData") or {}
    if not option_data.get("sceneId"):
        return False
    if not (option_data.get("next_options") or []):
        return False
    return True


def run_read_wait_suite(
    name: str,
    items: list[dict[str, Any]],
    read_wait_s: float,
    base_url: str,
    *,
    full_ready: bool = False,
    image_timeout_s: float = 240.0,
    image_poll_interval_s: float = 1.5,
    notes: str | None = None,
    profile: str = "default",
    second_click_placeholder_retries: int = 0,
    abort_on_full_ready_over_s: float | None = None,
    first_click_timeout_s: int | None = None,
    second_click_timeout_s: int = 1800,
) -> dict[str, Any]:
    session = requests.Session()
    runs: list[dict[str, Any]] = []
    suite_start = time.time()
    abort_reason: dict[str, Any] | None = None

    for item in items:
        run: dict[str, Any] = {
            "benchmark_id": item["benchmark_id"],
            "theme_id": item["theme_id"],
            "theme": item["theme"],
            "read_wait_s": read_wait_s,
            "full_ready_mode": full_ready,
            "profile": profile,
        }
        worldview = generate_worldview(session, base_url, item, profile=profile, read_wait_s=read_wait_s)
        run["worldview"] = worldview

        first_click: dict[str, Any] = {}
        second_click: dict[str, Any] = {}
        full_ready_result: dict[str, Any] = {}

        if worldview.get("http_status") == 200 and worldview.get("status") == "success":
            world_json = worldview.get("response_json") or {}
            global_state = merge_benchmark_flags(world_json.get("globalState") or {}, profile, read_wait_s)

            first_payload = {
                "option": "开始游戏",
                "optionIndex": 0,
                "sceneId": None,
                "globalState": global_state,
            }
            effective_first_click_timeout = first_click_timeout_s or second_click_timeout_s
            first_click = fetch_story_option_with_retry(
                session,
                base_url,
                first_payload,
                timeout_s=effective_first_click_timeout,
            )
            first_json = first_click.get("response_json") or {}
            first_click.update(
                {
                    "status": first_json.get("status"),
                    "has_scene": bool((first_json.get("optionData") or {}).get("scene")),
                    "has_image": bool(((first_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                    "is_placeholder": is_placeholder_option_data(first_json.get("optionData") or {})
                    if first_json.get("status") == "success"
                    else False,
                }
            )
            first_click["setup_success"] = compute_first_click_setup_success(first_click)

            option_data = first_json.get("optionData") or {}
            chosen_index, chosen_text = pick_option(option_data, "继续推进剧情")
            next_scene_id = option_data.get("sceneId")
            next_options = option_data.get("next_options") or []
            updated_global_state = apply_flow_update(global_state, option_data)

            if first_click.get("setup_success") and next_scene_id and next_options:
                time.sleep(read_wait_s)
                second_payload = {
                    "option": chosen_text,
                    "optionIndex": chosen_index,
                    "sceneId": next_scene_id,
                    "currentOptions": next_options,
                    "globalState": updated_global_state,
                    "previousSceneId": "initial",
                    "previousSceneImage": option_data.get("scene_image"),
                    "previousSceneText": option_data.get("scene") or "",
                }
                second_click = fetch_story_option_with_retry(
                    session,
                    base_url,
                    second_payload,
                    retries=second_click_placeholder_retries,
                    timeout_s=second_click_timeout_s,
                )
                second_json = second_click.get("response_json") or {}
                benchmark_diag = extract_benchmark_diagnostics(second_json)
                second_click.update(
                    {
                        "status": second_json.get("status"),
                        "has_scene": bool((second_json.get("optionData") or {}).get("scene")),
                        "has_image": bool(((second_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                        "selected_option_index": chosen_index,
                        "selected_option_text": chosen_text,
                        "input_scene_id": next_scene_id,
                        "inferred_cache_result": classify_second_click(second_click),
                        "is_placeholder": is_placeholder_option_data(second_json.get("optionData") or {})
                        if second_json.get("status") == "success"
                        else False,
                        "used_updated_flow_state": True,
                        "cache_hit_reason": benchmark_diag.get("cache_hit_reason"),
                        "cache_miss_reason": benchmark_diag.get("cache_miss_reason"),
                        "global_state_key_drift_detected": bool(benchmark_diag.get("global_state_key_drift_detected")),
                        "scene_id_mismatch_detected": bool(benchmark_diag.get("scene_id_mismatch_detected")),
                        "selected_option_mismatch_detected": bool(benchmark_diag.get("selected_option_mismatch_detected")),
                        "current_options_key_drift_detected": bool(benchmark_diag.get("current_options_key_drift_detected")),
                        "benchmark_diagnostics": benchmark_diag,
                    }
                )
                if full_ready:
                    full_ready_result = maybe_collect_full_ready(
                        session=session,
                        base_url=base_url,
                        item=item,
                        updated_global_state=updated_global_state,
                        second_click=second_click,
                        current_scene_id=next_scene_id,
                        previous_scene_image=option_data.get("scene_image"),
                        previous_scene_text=option_data.get("scene") or "",
                        image_timeout_s=image_timeout_s,
                        image_poll_interval_s=image_poll_interval_s,
                    )
                    run["long_tail_attribution"] = compute_long_tail_attribution(
                        {"second_click": second_click, "full_ready": full_ready_result}
                    )
                    full_ready_result["attribution"] = run["long_tail_attribution"]

        run["first_click"] = first_click
        run["second_click"] = second_click
        if full_ready:
            run["full_ready"] = full_ready_result
        else:
            run["full_ready"] = full_ready_result
        run["placeholder"] = bool((second_click or {}).get("is_placeholder"))
        run["transport_success"] = compute_transport_success(run, full_ready)
        run["strict_success"] = compute_strict_success(run, full_ready)
        run["failure_bucket"] = classify_failure_bucket(run, full_ready)
        run["cache_path_classification"] = classify_cache_path(run)
        run["cache_hit_reason"] = (second_click or {}).get("cache_hit_reason")
        run["cache_miss_reason"] = (second_click or {}).get("cache_miss_reason")
        run["global_state_key_drift_detected"] = bool((second_click or {}).get("global_state_key_drift_detected"))
        run["scene_id_mismatch_detected"] = bool((second_click or {}).get("scene_id_mismatch_detected"))
        run["selected_option_mismatch_detected"] = bool((second_click or {}).get("selected_option_mismatch_detected"))
        run["success"] = run["strict_success"]
        runs.append(run)
        if (
            abort_on_full_ready_over_s is not None
            and full_ready
            and isinstance((run.get("full_ready") or {}).get("full_ready_elapsed_s"), (int, float))
            and float(run["full_ready"]["full_ready_elapsed_s"]) > float(abort_on_full_ready_over_s)
        ):
            abort_reason = {
                "type": "extreme_tail_abort",
                "threshold_s": float(abort_on_full_ready_over_s),
                "benchmark_id": run.get("benchmark_id"),
                "theme": run.get("theme"),
                "full_ready_elapsed_s": float(run["full_ready"]["full_ready_elapsed_s"]),
                "ready_mode": (run.get("full_ready") or {}).get("ready_mode"),
                "second_click_placeholder": bool((run.get("second_click") or {}).get("is_placeholder")),
            }
            break

    suite_end = time.time()
    second_vals = [r["second_click"]["elapsed_s"] for r in runs if r.get("second_click", {}).get("http_status") == 200]
    first_click_vals = [r["first_click"]["elapsed_s"] for r in runs if r.get("first_click", {}).get("http_status") == 200]
    hit_count = sum(1 for r in runs if r.get("second_click", {}).get("inferred_cache_result") == "likely_hit")
    first_click_setup_success_count = sum(1 for r in runs if r.get("first_click", {}).get("setup_success"))
    transport_success_count = sum(1 for r in runs if r.get("transport_success"))
    strict_success_count = sum(1 for r in runs if r.get("strict_success"))
    failure_bucket_counts: dict[str, int] = {}
    cache_hit_reason_counts: dict[str, int] = {}
    cache_miss_reason_counts: dict[str, int] = {}
    global_state_key_drift_detected_count = 0
    scene_id_mismatch_detected_count = 0
    selected_option_mismatch_detected_count = 0
    for run in runs:
        bucket = run.get("failure_bucket")
        if not bucket:
            pass
        else:
            failure_bucket_counts[bucket] = failure_bucket_counts.get(bucket, 0) + 1
        hit_reason = run.get("cache_hit_reason")
        if hit_reason:
            cache_hit_reason_counts[hit_reason] = cache_hit_reason_counts.get(hit_reason, 0) + 1
        miss_reason = run.get("cache_miss_reason")
        if miss_reason:
            cache_miss_reason_counts[miss_reason] = cache_miss_reason_counts.get(miss_reason, 0) + 1
        if run.get("global_state_key_drift_detected"):
            global_state_key_drift_detected_count += 1
        if run.get("scene_id_mismatch_detected"):
            scene_id_mismatch_detected_count += 1
        if run.get("selected_option_mismatch_detected"):
            selected_option_mismatch_detected_count += 1
    summary: dict[str, Any] = {
        "experiment_name": name,
        "profile": profile,
        "sample_size": len(runs),
        "read_wait_s": read_wait_s,
        "suite_start_ts": suite_start,
        "suite_end_ts": suite_end,
        "first_click_elapsed_s": summarize_numeric(first_click_vals),
        "first_click_setup_success_count": first_click_setup_success_count,
        "second_click_elapsed_s": summarize_numeric(second_vals),
        "second_click_success_count": sum(1 for r in runs if r.get("second_click", {}).get("status") == "success"),
        "transport_success_count": transport_success_count,
        "strict_success_count": strict_success_count,
        "likely_hit_count": hit_count,
        "likely_hit_rate": round(hit_count / len(runs), 3) if runs else 0.0,
        "failure_bucket_counts": failure_bucket_counts,
        "placeholder_strict_fail_count": failure_bucket_counts.get("placeholder_strict_fail", 0),
        "cache_hit_reason_counts": cache_hit_reason_counts,
        "cache_miss_reason_counts": cache_miss_reason_counts,
        "global_state_key_drift_detected_count": global_state_key_drift_detected_count,
        "scene_id_mismatch_detected_count": scene_id_mismatch_detected_count,
        "selected_option_mismatch_detected_count": selected_option_mismatch_detected_count,
    }
    if abort_reason:
        summary["aborted"] = True
        summary["abort_reason"] = abort_reason
    else:
        summary["aborted"] = False

    if full_ready:
        text_vals = [
            float(r["full_ready"]["text_ready_elapsed_s"])
            for r in runs
            if isinstance(r.get("full_ready", {}).get("text_ready_elapsed_s"), (int, float))
        ]
        image_vals = [
            float(r["full_ready"]["image_ready_elapsed_s"])
            for r in runs
            if isinstance(r.get("full_ready", {}).get("image_ready_elapsed_s"), (int, float))
        ]
        full_vals = [
            float(r["full_ready"]["full_ready_elapsed_s"])
            for r in runs
            if isinstance(r.get("full_ready", {}).get("full_ready_elapsed_s"), (int, float))
        ]
        direct_image_count = sum(
            1 for r in runs if (r.get("full_ready", {}).get("ready_mode") == "direct_in_generate_option")
        )
        async_image_count = sum(
            1 for r in runs if (r.get("full_ready", {}).get("ready_mode") == "async_generate_scene_image")
        )
        placeholder_count = sum(1 for r in runs if bool((r.get("second_click") or {}).get("is_placeholder")))
        provider_retry_heavy_count = sum(
            1 for r in runs if int((r.get("long_tail_attribution") or {}).get("provider_retry_heavy_count", 0)) > 0
        )
        provider_429_count = sum(
            int((r.get("long_tail_attribution") or {}).get("provider_429_count", 0)) for r in runs
        )
        provider_timeout_count = sum(
            int((r.get("long_tail_attribution") or {}).get("provider_timeout_count", 0)) for r in runs
        )
        provider_backoff_wait_ms_total = sum(
            int((r.get("long_tail_attribution") or {}).get("provider_backoff_wait_ms_total", 0)) for r in runs
        )
        main_character_contention_suspected_count = sum(
            1
            for r in runs
            if bool((r.get("long_tail_attribution") or {}).get("main_character_contention_suspected"))
        )
        real_scene_count = sum(
            1
            for r in runs
            if r.get("second_click", {}).get("status") == "success" and not r.get("second_click", {}).get("is_placeholder")
        )
        summary.update(
            {
                "success_count": strict_success_count,
                "text_ready_elapsed_s": summarize_numeric(text_vals),
                "image_ready_elapsed_s": summarize_numeric(image_vals),
                "full_ready_elapsed_s": summarize_numeric(full_vals),
                "real_scene_count": real_scene_count,
                "real_scene_rate": round(real_scene_count / len(runs), 3) if runs else 0.0,
                "direct_image_count": direct_image_count,
                "async_image_count": async_image_count,
                "placeholder_count": placeholder_count,
                "placeholder_rate": round(placeholder_count / len(runs), 3) if runs else 0.0,
                "direct_image_rate": round(direct_image_count / len(runs), 3) if runs else 0.0,
                "async_image_rate": round(async_image_count / len(runs), 3) if runs else 0.0,
                "provider_retry_heavy_count": provider_retry_heavy_count,
                "provider_429_count": provider_429_count,
                "provider_timeout_count": provider_timeout_count,
                "provider_backoff_wait_ms_total": provider_backoff_wait_ms_total,
                "main_character_contention_suspected_count": main_character_contention_suspected_count,
                "notes": notes or "",
            }
        )

    return {
        "summary": summary,
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--read-wait", type=float, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--full-ready", action="store_true")
    parser.add_argument("--image-timeout", type=float, default=240.0)
    parser.add_argument("--image-poll-interval", type=float, default=1.5)
    parser.add_argument("--notes", default="")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--second-click-placeholder-retries", type=int, default=0)
    parser.add_argument("--abort-on-full-ready-over", type=float, default=None)
    parser.add_argument("--first-click-timeout", type=int, default=None)
    parser.add_argument("--second-click-timeout", type=int, default=1800)
    args = parser.parse_args()

    items = load_benchmark(limit=args.limit, offset=args.offset)
    payload = run_read_wait_suite(
        args.name,
        items,
        args.read_wait,
        args.base_url.rstrip("/"),
        full_ready=args.full_ready,
        image_timeout_s=args.image_timeout,
        image_poll_interval_s=args.image_poll_interval,
        notes=args.notes or None,
        profile=args.profile,
        second_click_placeholder_retries=args.second_click_placeholder_retries,
        abort_on_full_ready_over_s=args.abort_on_full_ready_over,
        first_click_timeout_s=args.first_click_timeout,
        second_click_timeout_s=args.second_click_timeout,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

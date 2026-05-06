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
BASE_URL = "http://127.0.0.1:5001"


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
    return {
        "event_count": len(events),
        "queue_wait_ms": summarize_numeric(queue_vals),
        "latency_ms": summarize_numeric(latency_vals),
        "llm_success_count": llm_success,
        "image_success_count": image_success,
        "request_thread_event_count": request_thread_events,
    }


def timed_post(
    session: requests.Session,
    path: str,
    payload: dict[str, Any],
    timeout_s: int = 1800,
) -> dict[str, Any]:
    start_wall = time.time()
    start_perf = time.perf_counter()
    resp = session.post(f"{BASE_URL}{path}", json=payload, timeout=timeout_s)
    elapsed = time.perf_counter() - start_perf
    end_wall = time.time()
    return {
        "http_status": resp.status_code,
        "elapsed_s": round(elapsed, 3),
        "response_json": safe_json(resp),
        "start_ts": start_wall,
        "end_ts": end_wall,
        "provider_events": summarize_provider_events(provider_events_in_window(start_wall, end_wall + 0.5)),
    }


def generate_worldview(session: requests.Session, item: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "gameTheme": item["theme"],
        "protagonistAttr": {},
        "difficulty": "涓瓑",
        "toneKey": "normal_ending",
        "imageStyle": item["image_style"],
    }
    run = timed_post(session, "/generate-worldview", payload)
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


def classify_second_click(second_click: dict[str, Any]) -> str:
    events = second_click.get("provider_events") or {}
    if events.get("llm_success_count", 0) == 0 and events.get("request_thread_event_count", 0) == 0:
        return "likely_hit"
    return "likely_miss_or_partial"


def run_read_wait_suite(name: str, items: list[dict[str, Any]], read_wait_s: float) -> dict[str, Any]:
    session = requests.Session()
    runs: list[dict[str, Any]] = []
    suite_start = time.time()

    for item in items:
        run: dict[str, Any] = {
            "benchmark_id": item["benchmark_id"],
            "theme_id": item["theme_id"],
            "theme": item["theme"],
            "read_wait_s": read_wait_s,
        }
        worldview = generate_worldview(session, item)
        run["worldview"] = worldview

        first_click: dict[str, Any] = {}
        second_click: dict[str, Any] = {}

        if worldview.get("http_status") == 200 and worldview.get("status") == "success":
            world_json = worldview.get("response_json") or {}
            global_state = world_json.get("globalState") or {}

            first_payload = {
                "option": "寮€濮嬫父鎴?",
                "optionIndex": 0,
                "sceneId": "initial",
                "globalState": global_state,
                "currentOptions": world_json.get("initialOptions") or [],
            }
            first_click = timed_post(session, "/generate-option", first_payload)
            first_json = first_click.get("response_json") or {}
            first_click.update(
                {
                    "status": first_json.get("status"),
                    "has_scene": bool((first_json.get("optionData") or {}).get("scene")),
                    "has_image": bool(((first_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                }
            )

            option_data = first_json.get("optionData") or {}
            chosen_index, chosen_text = pick_option(option_data, "缁х画鍓嶈繘")
            next_scene_id = option_data.get("sceneId")
            next_options = option_data.get("next_options") or []

            if next_scene_id and next_options:
                time.sleep(read_wait_s)
                second_payload = {
                    "option": chosen_text,
                    "optionIndex": chosen_index,
                    "sceneId": next_scene_id,
                    "globalState": global_state,
                    "currentOptions": next_options,
                    "previousSceneId": "initial",
                }
                second_click = timed_post(session, "/generate-option", second_payload)
                second_json = second_click.get("response_json") or {}
                second_click.update(
                    {
                        "status": second_json.get("status"),
                        "has_scene": bool((second_json.get("optionData") or {}).get("scene")),
                        "has_image": bool(((second_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                        "selected_option_index": chosen_index,
                        "selected_option_text": chosen_text,
                        "input_scene_id": next_scene_id,
                        "inferred_cache_result": classify_second_click(second_click),
                    }
                )

        run["first_click"] = first_click
        run["second_click"] = second_click
        runs.append(run)

    suite_end = time.time()
    second_vals = [r["second_click"]["elapsed_s"] for r in runs if r.get("second_click", {}).get("http_status") == 200]
    hit_count = sum(
        1 for r in runs if r.get("second_click", {}).get("inferred_cache_result") == "likely_hit"
    )

    return {
        "summary": {
            "experiment_name": name,
            "sample_size": len(runs),
            "read_wait_s": read_wait_s,
            "suite_start_ts": suite_start,
            "suite_end_ts": suite_end,
            "second_click_elapsed_s": summarize_numeric(second_vals),
            "second_click_success_count": sum(
                1 for r in runs if r.get("second_click", {}).get("status") == "success"
            ),
            "likely_hit_count": hit_count,
            "likely_hit_rate": round(hit_count / len(runs), 3) if runs else 0.0,
        },
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--read-wait", type=float, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    items = load_benchmark(limit=args.limit, offset=args.offset)
    payload = run_read_wait_suite(args.name, items, args.read_wait)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

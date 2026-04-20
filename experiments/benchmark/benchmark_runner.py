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
    if not isinstance(items, list):
        raise RuntimeError("benchmark items missing")
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
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "p95": round(percentile(values, 0.95) or 0.0, 3),
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
            ts = float(ts)
            if start_ts <= ts <= end_ts:
                rows.append(item)
    return rows


def summarize_provider_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    queue_vals = [float(e["queue_wait_ms"]) for e in events if isinstance(e.get("queue_wait_ms"), (int, float))]
    latency_vals = [float(e["latency_ms"]) for e in events if isinstance(e.get("latency_ms"), (int, float))]
    return {
        "event_count": len(events),
        "queue_wait_ms": summarize_numeric(queue_vals),
        "latency_ms": summarize_numeric(latency_vals),
    }


def generate_worldview(session: requests.Session, item: dict[str, Any], timeout_s: int = 1800) -> dict[str, Any]:
    payload = {
        "gameTheme": item["theme"],
        "protagonistAttr": {},
        "difficulty": "中等",
        "toneKey": "normal_ending",
        "imageStyle": item["image_style"],
    }
    start_wall = time.time()
    start_perf = time.perf_counter()
    resp = session.post(f"{BASE_URL}/generate-worldview", json=payload, timeout=timeout_s)
    elapsed = time.perf_counter() - start_perf
    end_wall = time.time()
    data = safe_json(resp)
    global_state = data.get("globalState") if isinstance(data.get("globalState"), dict) else {}
    return {
        "benchmark_id": item["benchmark_id"],
        "theme_id": item["theme_id"],
        "theme": item["theme"],
        "image_style": item["image_style"],
        "http_status": resp.status_code,
        "elapsed_s": round(elapsed, 3),
        "status": data.get("status"),
        "response_json": data,
        "game_id": data.get("gameId") or data.get("game_id") or global_state.get("game_id"),
        "start_ts": start_wall,
        "end_ts": end_wall,
    }


def wait_main_character(game_id: str, timeout_s: int = 240, poll_s: float = 2.0) -> dict[str, Any]:
    session = requests.Session()
    start = time.perf_counter()
    history = []
    while True:
        resp = session.get(f"{BASE_URL}/main-character-status/{game_id}", timeout=60)
        data = safe_json(resp)
        history.append({"elapsed_s": round(time.perf_counter() - start, 3), "http_status": resp.status_code, **data})
        if data.get("status") == "completed" and data.get("ready") is True:
            return {"completed": True, "elapsed_s": round(time.perf_counter() - start, 3), "history": history}
        if time.perf_counter() - start >= timeout_s:
            return {"completed": False, "elapsed_s": round(time.perf_counter() - start, 3), "history": history}
        time.sleep(poll_s)


def run_worldview_suite(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    session = requests.Session()
    runs = []
    suite_start = time.time()
    for item in items:
        run = generate_worldview(session, item)
        run["provider_events"] = summarize_provider_events(provider_events_in_window(run["start_ts"], run["end_ts"] + 0.5))
        runs.append(run)
    suite_end = time.time()
    elapsed_vals = [r["elapsed_s"] for r in runs if r.get("http_status") == 200]
    return {
        "summary": {
            "experiment_name": name,
            "sample_size": len(runs),
            "suite_start_ts": suite_start,
            "suite_end_ts": suite_end,
            "elapsed_s": summarize_numeric(elapsed_vals),
            "success_count": sum(1 for r in runs if r.get("status") == "success"),
            "error_count": sum(1 for r in runs if r.get("status") != "success"),
        },
        "runs": runs,
    }


def run_fullchain_suite(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    session = requests.Session()
    runs = []
    suite_start = time.time()
    for item in items:
        worldview = generate_worldview(session, item)
        option_result: dict[str, Any] = {}
        protagonist_result: dict[str, Any] = {}
        if worldview.get("http_status") == 200 and worldview.get("status") == "success":
            global_state = worldview.get("response_json", {}).get("globalState")
            world_json = worldview.get("response_json", {})
            payload = {
                "option": "开始游戏",
                "optionIndex": 0,
                "sceneId": "initial",
                "globalState": global_state,
                "currentOptions": world_json.get("initialOptions") or [],
            }
            opt_start_wall = time.time()
            opt_start_perf = time.perf_counter()
            opt_resp = session.post(f"{BASE_URL}/generate-option", json=payload, timeout=1800)
            opt_elapsed = time.perf_counter() - opt_start_perf
            opt_end_wall = time.time()
            opt_json = safe_json(opt_resp)
            option_result = {
                "http_status": opt_resp.status_code,
                "elapsed_s": round(opt_elapsed, 3),
                "status": opt_json.get("status"),
                "response_json": opt_json,
                "has_scene": bool((opt_json.get("optionData") or {}).get("scene")),
                "has_image": bool(((opt_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                "start_ts": opt_start_wall,
                "end_ts": opt_end_wall,
            }
            if worldview.get("game_id"):
                protagonist_result = wait_main_character(str(worldview["game_id"]))
        start_ts = worldview.get("start_ts", time.time())
        end_ts = max(worldview.get("end_ts", start_ts), option_result.get("end_ts", start_ts), time.time())
        runs.append(
            {
                "benchmark_id": item["benchmark_id"],
                "theme_id": item["theme_id"],
                "theme": item["theme"],
                "worldview": worldview,
                "generate_option": option_result,
                "main_character": protagonist_result,
                "provider_events": summarize_provider_events(provider_events_in_window(start_ts, end_ts + 0.5)),
            }
        )
    suite_end = time.time()
    worldview_vals = [r["worldview"]["elapsed_s"] for r in runs if r["worldview"].get("http_status") == 200]
    option_vals = [r["generate_option"]["elapsed_s"] for r in runs if r.get("generate_option", {}).get("http_status") == 200]
    protagonist_vals = [r["main_character"]["elapsed_s"] for r in runs if r.get("main_character", {}).get("completed")]
    return {
        "summary": {
            "experiment_name": name,
            "sample_size": len(runs),
            "suite_start_ts": suite_start,
            "suite_end_ts": suite_end,
            "worldview_elapsed_s": summarize_numeric(worldview_vals),
            "generate_option_elapsed_s": summarize_numeric(option_vals),
            "main_character_completion_s": summarize_numeric(protagonist_vals),
            "full_success_count": sum(
                1
                for r in runs
                if r["worldview"].get("status") == "success"
                and r["generate_option"].get("status") == "success"
                and r["main_character"].get("completed") is True
            ),
        },
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["worldview", "fullchain"], required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    items = load_benchmark(limit=args.limit, offset=args.offset)
    if args.mode == "worldview":
        payload = run_worldview_suite(args.name, items)
    else:
        payload = run_fullchain_suite(args.name, items)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

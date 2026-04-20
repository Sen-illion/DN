from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "experiments" / "efficiency_postfix"
THEMES_FILE = REPO_ROOT / "game_themes_100.json"
PROVIDER_EVENTS_FILE = REPO_ROOT / "logs" / "provider_events.jsonl"
BASE_URL = "http://127.0.0.1:5001"


def load_themes(limit: int, offset: int = 0) -> list[dict[str, Any]]:
    payload = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise RuntimeError("game_themes_100.json items is not a list")
    picked = []
    for item in items[offset : offset + limit]:
        if not isinstance(item, dict):
            continue
        theme = str(item.get("theme") or "").strip()
        if not theme:
            continue
        picked.append(item)
    return picked


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    idx = (len(ordered) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return float(ordered[lo])
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"_raw": data}
    except Exception:
        return {"_raw_text": response.text[:4000]}


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
    queue_waits = [
        float(item["queue_wait_ms"])
        for item in events
        if isinstance(item.get("queue_wait_ms"), (int, float))
    ]
    latencies = [
        float(item["latency_ms"])
        for item in events
        if isinstance(item.get("latency_ms"), (int, float))
    ]
    by_group: dict[str, dict[str, Any]] = {}
    for item in events:
        key = f'{item.get("kind", "unknown")} / {item.get("provider", "unknown")} / {item.get("request_type", "unknown")}'
        group = by_group.setdefault(
            key,
            {
                "events": 0,
                "statuses": {},
                "queue_wait_ms": [],
                "latency_ms": [],
            },
        )
        group["events"] += 1
        status = str(item.get("status") or "unknown")
        group["statuses"][status] = group["statuses"].get(status, 0) + 1
        if isinstance(item.get("queue_wait_ms"), (int, float)):
            group["queue_wait_ms"].append(float(item["queue_wait_ms"]))
        if isinstance(item.get("latency_ms"), (int, float)):
            group["latency_ms"].append(float(item["latency_ms"]))

    compact_groups: dict[str, Any] = {}
    for key, group in by_group.items():
        compact_groups[key] = {
            "events": group["events"],
            "statuses": group["statuses"],
            "queue_wait_ms": summarize_numeric(group["queue_wait_ms"]),
            "latency_ms": summarize_numeric(group["latency_ms"]),
        }

    return {
        "event_count": len(events),
        "queue_wait_ms": summarize_numeric(queue_waits),
        "latency_ms": summarize_numeric(latencies),
        "groups": compact_groups,
    }


def generate_worldview(
    session: requests.Session,
    theme_item: dict[str, Any],
    timeout_s: int = 1800,
) -> dict[str, Any]:
    payload = {
        "gameTheme": theme_item["theme"],
        "protagonistAttr": {},
        "difficulty": "中等",
        "toneKey": "normal_ending",
        "imageStyle": theme_item.get("image_style") or {"type": "realistic"},
    }
    start_wall = time.time()
    start_perf = time.perf_counter()
    response = session.post(f"{BASE_URL}/generate-worldview", json=payload, timeout=timeout_s)
    elapsed = time.perf_counter() - start_perf
    end_wall = time.time()
    data = safe_json(response)
    global_state = data.get("globalState") if isinstance(data.get("globalState"), dict) else {}
    game_id = data.get("gameId") or data.get("game_id") or global_state.get("game_id")
    return {
        "theme_id": theme_item.get("id"),
        "theme": theme_item.get("theme"),
        "image_style": theme_item.get("image_style"),
        "request_payload": payload,
        "http_status": response.status_code,
        "elapsed_s": round(elapsed, 3),
        "start_ts": start_wall,
        "end_ts": end_wall,
        "response_json": data,
        "status": data.get("status"),
        "game_id": game_id,
        "has_global_state": bool(global_state),
    }


def run_worldview_suite(name: str, sample_size: int, offset: int = 0) -> dict[str, Any]:
    session = requests.Session()
    themes = load_themes(sample_size, offset=offset)
    results = []
    suite_start = time.time()
    for theme_item in themes:
        result = generate_worldview(session, theme_item)
        result["provider_events"] = summarize_provider_events(
            provider_events_in_window(result["start_ts"], result["end_ts"] + 0.5)
        )
        results.append(result)
    suite_end = time.time()
    elapsed_values = [row["elapsed_s"] for row in results if row.get("http_status") == 200]
    queue_means = []
    for row in results:
        q = row.get("provider_events", {}).get("queue_wait_ms", {}).get("mean")
        if isinstance(q, (int, float)):
            queue_means.append(float(q))
    summary = {
        "experiment_name": name,
        "sample_size": len(results),
        "suite_start_ts": suite_start,
        "suite_end_ts": suite_end,
        "elapsed_s": summarize_numeric(elapsed_values),
        "provider_queue_wait_ms_mean_per_run": summarize_numeric(queue_means),
        "success_count": sum(1 for row in results if row.get("http_status") == 200 and row.get("status") == "success"),
        "error_count": sum(1 for row in results if row.get("http_status") != 200 or row.get("status") != "success"),
    }
    return {"summary": summary, "runs": results}


def wait_main_character(game_id: str, timeout_s: int = 240, poll_s: float = 2.0) -> dict[str, Any]:
    session = requests.Session()
    start = time.perf_counter()
    history = []
    while True:
        response = session.get(f"{BASE_URL}/main-character-status/{game_id}", timeout=60)
        data = safe_json(response)
        history.append(
            {
                "elapsed_s": round(time.perf_counter() - start, 3),
                "http_status": response.status_code,
                **data,
            }
        )
        if data.get("status") == "completed" and data.get("ready") is True:
            return {
                "completed": True,
                "elapsed_s": round(time.perf_counter() - start, 3),
                "history": history,
            }
        if time.perf_counter() - start >= timeout_s:
            return {
                "completed": False,
                "elapsed_s": round(time.perf_counter() - start, 3),
                "history": history,
            }
        time.sleep(poll_s)


def run_full_chain_suite(name: str, sample_size: int, offset: int = 0) -> dict[str, Any]:
    session = requests.Session()
    themes = load_themes(sample_size, offset=offset)
    runs = []
    suite_start = time.time()
    for theme_item in themes:
        worldview = generate_worldview(session, theme_item)
        option_result: dict[str, Any] = {}
        protagonist_result: dict[str, Any] = {}
        if worldview.get("http_status") == 200 and worldview.get("status") == "success":
            global_state = worldview.get("response_json", {}).get("globalState")
            world_json = worldview.get("response_json", {})
            current_options = world_json.get("initialOptions") or []
            payload = {
                "option": "开始游戏",
                "optionIndex": 0,
                "sceneId": "initial",
                "globalState": global_state,
                "currentOptions": current_options,
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
                "start_ts": opt_start_wall,
                "end_ts": opt_end_wall,
                "response_json": opt_json,
                "status": opt_json.get("status"),
                "has_scene": bool((opt_json.get("optionData") or {}).get("scene")),
                "has_image": bool(((opt_json.get("optionData") or {}).get("scene_image") or {}).get("url")),
                "scene_id": (opt_json.get("optionData") or {}).get("sceneId"),
            }
            game_id = worldview.get("game_id")
            if isinstance(game_id, str) and game_id:
                protagonist_result = wait_main_character(game_id)
        run = {
            "theme_id": theme_item.get("id"),
            "theme": theme_item.get("theme"),
            "worldview": worldview,
            "generate_option": option_result,
            "main_character": protagonist_result,
        }
        win_start = worldview.get("start_ts", time.time())
        win_end = max(
            worldview.get("end_ts", win_start),
            option_result.get("end_ts", win_start),
            time.time(),
        )
        run["provider_events"] = summarize_provider_events(provider_events_in_window(win_start, win_end + 0.5))
        runs.append(run)
    suite_end = time.time()

    worldview_elapsed = [row["worldview"]["elapsed_s"] for row in runs if row["worldview"].get("http_status") == 200]
    option_elapsed = [row["generate_option"]["elapsed_s"] for row in runs if row.get("generate_option", {}).get("http_status") == 200]
    protagonist_elapsed = [row["main_character"]["elapsed_s"] for row in runs if row.get("main_character", {}).get("completed")]
    summary = {
        "experiment_name": name,
        "sample_size": len(runs),
        "suite_start_ts": suite_start,
        "suite_end_ts": suite_end,
        "worldview_elapsed_s": summarize_numeric(worldview_elapsed),
        "generate_option_elapsed_s": summarize_numeric(option_elapsed),
        "main_character_completion_s": summarize_numeric(protagonist_elapsed),
        "full_success_count": sum(
            1
            for row in runs
            if row["worldview"].get("status") == "success"
            and row["generate_option"].get("status") == "success"
            and row["main_character"].get("completed") is True
        ),
    }
    return {"summary": summary, "runs": runs}


def run_one_worldview_concurrent(theme_item: dict[str, Any]) -> dict[str, Any]:
    with requests.Session() as session:
        return generate_worldview(session, theme_item)


def run_concurrency_suite(name: str, sample_size: int, concurrency_levels: list[int], offset: int = 0) -> dict[str, Any]:
    themes = load_themes(sample_size, offset=offset)
    levels = []
    for concurrency in concurrency_levels:
        start_ts = time.time()
        started_perf = time.perf_counter()
        results = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(run_one_worldview_concurrent, item) for item in themes]
            for future in as_completed(futures):
                results.append(future.result())
        end_ts = time.time()
        wall_elapsed = time.perf_counter() - started_perf
        provider_summary = summarize_provider_events(provider_events_in_window(start_ts, end_ts + 0.5))
        elapsed_values = [row["elapsed_s"] for row in results if row.get("http_status") == 200]
        levels.append(
            {
                "concurrency": concurrency,
                "sample_size": len(results),
                "start_ts": start_ts,
                "end_ts": end_ts,
                "wall_elapsed_s": round(wall_elapsed, 3),
                "throughput_runs_per_min": round((len(results) / wall_elapsed) * 60.0, 3) if wall_elapsed > 0 else None,
                "elapsed_s": summarize_numeric(elapsed_values),
                "success_count": sum(1 for row in results if row.get("http_status") == 200 and row.get("status") == "success"),
                "provider_events": provider_summary,
                "runs": sorted(results, key=lambda row: (row.get("start_ts", 0.0), str(row.get("theme_id")))),
            }
        )
    return {"experiment_name": name, "levels": levels}


def write_output(filename: str, payload: dict[str, Any]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    worldview = sub.add_parser("worldview")
    worldview.add_argument("--name", required=True)
    worldview.add_argument("--sample-size", type=int, required=True)
    worldview.add_argument("--offset", type=int, default=0)
    worldview.add_argument("--output", required=True)

    fullchain = sub.add_parser("fullchain")
    fullchain.add_argument("--name", required=True)
    fullchain.add_argument("--sample-size", type=int, required=True)
    fullchain.add_argument("--offset", type=int, default=0)
    fullchain.add_argument("--output", required=True)

    concurrency = sub.add_parser("concurrency")
    concurrency.add_argument("--name", required=True)
    concurrency.add_argument("--sample-size", type=int, required=True)
    concurrency.add_argument("--offset", type=int, default=0)
    concurrency.add_argument("--levels", required=True, help="comma-separated, e.g. 1,3,5")
    concurrency.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.command == "worldview":
        payload = run_worldview_suite(args.name, args.sample_size, offset=args.offset)
    elif args.command == "fullchain":
        payload = run_full_chain_suite(args.name, args.sample_size, offset=args.offset)
    else:
        levels = [int(item.strip()) for item in args.levels.split(",") if item.strip()]
        payload = run_concurrency_suite(args.name, args.sample_size, levels, offset=args.offset)

    path = write_output(args.output, payload)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

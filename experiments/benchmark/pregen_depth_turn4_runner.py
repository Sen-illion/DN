from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from pregen_read_wait_runner import (
    DEFAULT_BASE_URL,
    REPO_ROOT,
    apply_flow_update,
    compute_long_tail_attribution,
    compute_first_click_setup_success,
    fetch_story_option_with_retry,
    generate_worldview,
    is_placeholder_option_data,
    load_benchmark,
    maybe_collect_full_ready,
    merge_benchmark_flags,
    pick_option,
    summarize_numeric,
)


OUTPUT_DIR = REPO_ROOT / "experiments" / "benchmark" / "standard_runs"
DEFAULT_DATASET_ROOT = (
    REPO_ROOT
    / "experiments"
    / "organized"
    / "ablations"
    / "02_pregeneration_ablation"
    / "datasets"
)


def load_items_from_file(path: Path, *, limit: int | None, offset: int) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_items = payload.get("items") or []
    else:
        raw_items = []
    items = [item for item in raw_items if isinstance(item, dict)]
    if offset:
        items = items[offset:]
    if limit is not None:
        items = items[:limit]
    return items


def _copy_local_image(image_url: str | None, out_path: Path) -> str | None:
    if not image_url:
        return None
    parsed = urlparse(str(image_url))
    source: Path | None = None
    if parsed.scheme in {"http", "https"}:
        source = REPO_ROOT / parsed.path.lstrip("/")
    elif str(image_url).startswith("/"):
        source = REPO_ROOT / str(image_url).lstrip("/")
    elif str(image_url).startswith("static/"):
        source = REPO_ROOT / str(image_url)
    if source is None or (not source.exists()):
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, out_path)
    return str(out_path)


def _first_option(option_data: dict[str, Any], fallback_text: str) -> tuple[int, str]:
    return pick_option(option_data, fallback_text)


def _turn_failure_bucket(turn_row: dict[str, Any]) -> str | None:
    if turn_row.get("strict_success"):
        return None
    click = turn_row.get("click") or {}
    full = turn_row.get("full_ready") or {}
    if click.get("request_error") == "timeout" or click.get("status") == "timeout":
        return "turn_click_timeout"
    if click.get("status") != "success":
        return "turn_click_not_success"
    if click.get("is_placeholder") and not click.get("has_image"):
        return "placeholder_no_image"
    probe = full.get("image_probe") or {}
    if probe.get("status") == "timeout" or full.get("error") == "scene_image_probe_failed":
        return "image_probe_timeout"
    if click.get("is_placeholder"):
        return "placeholder_strict_fail"
    return "other"


def _extract_turn_scene(option_data: dict[str, Any]) -> dict[str, Any]:
    scene_image = option_data.get("scene_image") or {}
    return {
        "scene_id": option_data.get("sceneId"),
        "scene_text": str(option_data.get("scene") or ""),
        "next_options": list(option_data.get("next_options") or []),
        "flow_update": option_data.get("flow_update") or {},
        "scene_image_url": scene_image.get("url"),
        "scene_image_prompt": scene_image.get("prompt"),
        "scene_image_style": scene_image.get("style"),
    }


def run_depth_suite(
    *,
    name: str,
    items: list[dict[str, Any]],
    base_url: str,
    read_wait_s: float,
    pregen_depth: int,
    turn_count: int,
    profile: str,
    image_timeout_s: float,
    image_poll_interval_s: float,
    first_click_timeout_s: int,
    turn_click_timeout_s: int,
    notes: str | None,
) -> dict[str, Any]:
    session = requests.Session()
    runs: list[dict[str, Any]] = []
    suite_start = time.time()
    benchmark_flags = {
        "_benchmark_pregen_depth": int(pregen_depth),
        "_benchmark_pregen_semantics": "fixed_path",
        "_benchmark_selection_policy": "first_option",
        "_benchmark_turn_count": int(turn_count),
        "_benchmark_path_trace": [],
        "_benchmark_turn_index": 0,
    }

    for item in items:
        run: dict[str, Any] = {
            "benchmark_id": item.get("benchmark_id"),
            "theme_id": item.get("theme_id"),
            "theme": item.get("theme"),
            "pregen_depth": pregen_depth,
            "turn_count": turn_count,
            "read_wait_s": read_wait_s,
            "selection_policy": "first_option",
            "profile": profile,
            "selected_option_indices": [],
            "turns": [],
            "notes": "",
        }

        worldview = generate_worldview(session, base_url, item, profile=profile, read_wait_s=read_wait_s)
        run["worldview"] = worldview
        if worldview.get("http_status") != 200 or worldview.get("status") != "success":
            run["success"] = False
            run["failure_bucket"] = "worldview_failed"
            runs.append(run)
            continue

        world_json = worldview.get("response_json") or {}
        global_state = merge_benchmark_flags(world_json.get("globalState") or {}, profile, read_wait_s)
        global_state.update(benchmark_flags)

        first_payload = {
            "option": "开始游戏",
            "optionIndex": 0,
            "sceneId": None,
            "globalState": global_state,
        }
        first_click = fetch_story_option_with_retry(
            session,
            base_url,
            first_payload,
            timeout_s=first_click_timeout_s,
            retries=0,
        )
        first_json = first_click.get("response_json") or {}
        first_option_data = first_json.get("optionData") or {}
        first_click.update(
            {
                "status": first_json.get("status"),
                "has_scene": bool((first_option_data or {}).get("scene")),
                "has_image": bool(((first_option_data or {}).get("scene_image") or {}).get("url")),
                "is_placeholder": is_placeholder_option_data(first_option_data)
                if first_json.get("status") == "success"
                else False,
            }
        )
        first_click["setup_success"] = compute_first_click_setup_success(first_click)
        run["first_click"] = first_click

        turn1 = {
            "turn_index": 1,
            "status": first_click.get("status"),
            "strict_success": bool(first_click.get("setup_success") and not first_click.get("is_placeholder")),
            "text_ready_elapsed_s": first_click.get("elapsed_s"),
            "image_ready_elapsed_s": first_click.get("elapsed_s") if first_click.get("has_image") else None,
            "full_ready_elapsed_s": first_click.get("elapsed_s") if first_click.get("has_image") else None,
            "selected_option_index": None,
            "selected_option_text": None,
            "click": first_click,
            "full_ready": {},
            "failure_bucket": None,
            **_extract_turn_scene(first_option_data),
        }
        run["turns"].append(turn1)

        if not first_click.get("setup_success"):
            run["success"] = False
            run["failure_bucket"] = "first_click_setup_failed"
            for missing_turn in range(2, turn_count + 1):
                run["turns"].append(
                    {
                        "turn_index": missing_turn,
                        "status": "skipped",
                        "strict_success": False,
                        "failure_bucket": "previous_turn_failed",
                    }
                )
            runs.append(run)
            continue

        current_global_state = apply_flow_update(global_state, first_option_data)
        current_option_data = first_option_data
        previous_scene_id: str | None = "initial"
        blocked = False

        for turn_index in range(2, turn_count + 1):
            if blocked:
                run["turns"].append(
                    {
                        "turn_index": turn_index,
                        "status": "skipped",
                        "strict_success": False,
                        "failure_bucket": "previous_turn_failed",
                    }
                )
                continue

            next_options = list(current_option_data.get("next_options") or [])
            scene_id = current_option_data.get("sceneId")
            if (not next_options) or (not scene_id):
                blocked = True
                run["turns"].append(
                    {
                        "turn_index": turn_index,
                        "status": "failed",
                        "strict_success": False,
                        "failure_bucket": "missing_next_options_or_scene_id",
                    }
                )
                continue

            if read_wait_s > 0:
                time.sleep(read_wait_s)

            chosen_index, chosen_text = _first_option(current_option_data, "继续推进剧情")
            run["selected_option_indices"].append(chosen_index)

            click_global_state = json.loads(json.dumps(current_global_state, ensure_ascii=False))
            click_global_state["_benchmark_turn_index"] = turn_index - 1
            click_global_state["_benchmark_path_trace"] = list(run["selected_option_indices"])
            click_payload = {
                "option": chosen_text,
                "optionIndex": chosen_index,
                "sceneId": scene_id,
                "currentOptions": next_options,
                "globalState": click_global_state,
                "previousSceneId": previous_scene_id,
                "previousSceneImage": current_option_data.get("scene_image"),
                "previousSceneText": current_option_data.get("scene") or "",
            }
            click = fetch_story_option_with_retry(
                session,
                base_url,
                click_payload,
                retries=0,
                timeout_s=turn_click_timeout_s,
            )
            click_json = click.get("response_json") or {}
            click_option_data = click_json.get("optionData") or {}
            click.update(
                {
                    "status": click_json.get("status"),
                    "has_scene": bool((click_option_data or {}).get("scene")),
                    "has_image": bool(((click_option_data or {}).get("scene_image") or {}).get("url")),
                    "is_placeholder": is_placeholder_option_data(click_option_data)
                    if click_json.get("status") == "success"
                    else False,
                    "selected_option_index": chosen_index,
                    "selected_option_text": chosen_text,
                    "input_scene_id": scene_id,
                }
            )

            full_ready = maybe_collect_full_ready(
                session=session,
                base_url=base_url,
                item=item,
                updated_global_state=current_global_state,
                second_click=click,
                current_scene_id=scene_id,
                previous_scene_image=current_option_data.get("scene_image"),
                previous_scene_text=current_option_data.get("scene") or "",
                image_timeout_s=image_timeout_s,
                image_poll_interval_s=image_poll_interval_s,
            )
            turn_row: dict[str, Any] = {
                "turn_index": turn_index,
                "status": click.get("status"),
                "selected_option_index": chosen_index,
                "selected_option_text": chosen_text,
                "click": click,
                "full_ready": full_ready,
                "text_ready_elapsed_s": full_ready.get("text_ready_elapsed_s"),
                "image_ready_elapsed_s": full_ready.get("image_ready_elapsed_s"),
                "full_ready_elapsed_s": full_ready.get("full_ready_elapsed_s"),
                **_extract_turn_scene(click_option_data),
            }
            turn_row["strict_success"] = bool(
                isinstance(turn_row.get("full_ready_elapsed_s"), (int, float)) and not click.get("is_placeholder")
            )
            turn_row["failure_bucket"] = _turn_failure_bucket(turn_row)
            turn_row["long_tail_attribution"] = compute_long_tail_attribution(
                {"second_click": click, "full_ready": full_ready}
            )
            run["turns"].append(turn_row)

            if turn_row["strict_success"]:
                current_global_state = apply_flow_update(current_global_state, click_option_data)
                current_option_data = click_option_data
                previous_scene_id = scene_id
            else:
                blocked = True

        measured = [
            float(turn.get("full_ready_elapsed_s"))
            for turn in run["turns"]
            if int(turn.get("turn_index", 0)) in {2, 3, 4}
            and isinstance(turn.get("full_ready_elapsed_s"), (int, float))
            and bool(turn.get("strict_success"))
        ]
        run["avg_generation_speed_s"] = round(statistics.mean(measured), 3) if measured else None
        run["success"] = bool(
            len([1 for turn in run["turns"] if int(turn.get("turn_index", 0)) in {2, 3, 4}]) >= 3
            and all(
                bool(turn.get("strict_success"))
                for turn in run["turns"]
                if int(turn.get("turn_index", 0)) in {2, 3, 4}
            )
        )
        run["failure_bucket"] = None if run["success"] else "turn2_4_not_all_success"
        runs.append(run)

    suite_end = time.time()

    turn_values: dict[int, list[float]] = {2: [], 3: [], 4: []}
    text_values: list[float] = []
    image_values: list[float] = []
    full_values: list[float] = []
    avg_values: list[float] = []
    placeholder_count = 0
    strict_success_count = 0
    provider_429_count = 0
    provider_timeout_count = 0
    provider_retry_heavy_count = 0
    direct_image_count = 0
    async_image_count = 0
    failure_bucket_counts: dict[str, int] = {}

    for run in runs:
        if isinstance(run.get("avg_generation_speed_s"), (int, float)):
            avg_values.append(float(run["avg_generation_speed_s"]))
        for turn in run.get("turns") or []:
            idx = int(turn.get("turn_index", 0) or 0)
            if idx not in {2, 3, 4}:
                continue
            if turn.get("strict_success"):
                strict_success_count += 1
            bucket = turn.get("failure_bucket")
            if bucket:
                failure_bucket_counts[bucket] = failure_bucket_counts.get(bucket, 0) + 1
            click = turn.get("click") or {}
            if click.get("is_placeholder"):
                placeholder_count += 1
            full = turn.get("full_ready") or {}
            if isinstance(full.get("text_ready_elapsed_s"), (int, float)):
                text_values.append(float(full["text_ready_elapsed_s"]))
            if isinstance(full.get("image_ready_elapsed_s"), (int, float)):
                image_values.append(float(full["image_ready_elapsed_s"]))
            if isinstance(full.get("full_ready_elapsed_s"), (int, float)):
                full_values.append(float(full["full_ready_elapsed_s"]))
                turn_values[idx].append(float(full["full_ready_elapsed_s"]))
            if full.get("ready_mode") == "direct_in_generate_option":
                direct_image_count += 1
            elif full.get("ready_mode") == "async_generate_scene_image":
                async_image_count += 1
            attr = turn.get("long_tail_attribution") or {}
            provider_429_count += int(attr.get("provider_429_count", 0) or 0)
            provider_timeout_count += int(attr.get("provider_timeout_count", 0) or 0)
            provider_retry_heavy_count += int(attr.get("provider_retry_heavy_count", 0) or 0)

    turn_attempts = len(runs) * max(0, turn_count - 1)
    summary = {
        "experiment_name": name,
        "profile": profile,
        "pregen_depth": pregen_depth,
        "pregen_semantics": "fixed_path",
        "selection_policy": "first_option",
        "turn_count": turn_count,
        "sample_size": len(runs),
        "read_wait_s": read_wait_s,
        "suite_start_ts": suite_start,
        "suite_end_ts": suite_end,
        "runs_success_count": sum(1 for run in runs if run.get("success")),
        "turn_attempt_count": turn_attempts,
        "strict_success_count": strict_success_count,
        "strict_success_rate": round(strict_success_count / turn_attempts, 3) if turn_attempts else 0.0,
        "turn2_full_ready_elapsed_s": summarize_numeric(turn_values[2]),
        "turn3_full_ready_elapsed_s": summarize_numeric(turn_values[3]),
        "turn4_full_ready_elapsed_s": summarize_numeric(turn_values[4]),
        "turn2_full_ready_mean_s": summarize_numeric(turn_values[2]).get("mean"),
        "turn3_full_ready_mean_s": summarize_numeric(turn_values[3]).get("mean"),
        "turn4_full_ready_mean_s": summarize_numeric(turn_values[4]).get("mean"),
        "text_ready_elapsed_s": summarize_numeric(text_values),
        "image_ready_elapsed_s": summarize_numeric(image_values),
        "full_ready_elapsed_s": summarize_numeric(full_values),
        "avg_generation_speed_s": round(statistics.mean(avg_values), 3) if avg_values else None,
        "avg_generation_speed_p95_s": summarize_numeric(avg_values).get("p95"),
        "placeholder_count": placeholder_count,
        "placeholder_rate": round(placeholder_count / turn_attempts, 3) if turn_attempts else 0.0,
        "direct_image_count": direct_image_count,
        "async_image_count": async_image_count,
        "direct_image_rate": round(direct_image_count / turn_attempts, 3) if turn_attempts else 0.0,
        "async_image_rate": round(async_image_count / turn_attempts, 3) if turn_attempts else 0.0,
        "provider_429_count": provider_429_count,
        "provider_timeout_count": provider_timeout_count,
        "provider_retry_heavy_count": provider_retry_heavy_count,
        "failure_bucket_counts": failure_bucket_counts,
        "notes": notes or "",
    }
    return {"summary": summary, "runs": runs}


def export_dataset_pack(
    *,
    payload: dict[str, Any],
    out_root: Path,
) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []
    for run in payload.get("runs") or []:
        benchmark_id = run.get("benchmark_id") or "unknown"
        item_dir = out_root / benchmark_id
        item_dir.mkdir(parents=True, exist_ok=True)

        turn_manifests: list[dict[str, Any]] = []
        for turn in run.get("turns") or []:
            turn_idx = turn.get("turn_index")
            image_url = turn.get("scene_image_url")
            local_copy = None
            if isinstance(turn_idx, int):
                local_copy = _copy_local_image(image_url, item_dir / f"turn{turn_idx}.png")
            turn_record = {
                "turn_index": turn_idx,
                "status": turn.get("status"),
                "strict_success": bool(turn.get("strict_success")),
                "failure_bucket": turn.get("failure_bucket"),
                "selected_option_index": turn.get("selected_option_index"),
                "selected_option_text": turn.get("selected_option_text"),
                "scene_id": turn.get("scene_id"),
                "scene_text": turn.get("scene_text"),
                "scene_image_url": image_url,
                "scene_image_local_path": local_copy,
                "text_ready_elapsed_s": turn.get("text_ready_elapsed_s"),
                "image_ready_elapsed_s": turn.get("image_ready_elapsed_s"),
                "full_ready_elapsed_s": turn.get("full_ready_elapsed_s"),
            }
            turn_manifests.append(turn_record)
            if isinstance(turn_idx, int) and turn_idx in {2, 3, 4}:
                item_rows.append(
                    {
                        "benchmark_id": benchmark_id,
                        "theme": run.get("theme"),
                        "turn_index": turn_idx,
                        "strict_success": bool(turn.get("strict_success")),
                        "full_ready_elapsed_s": turn.get("full_ready_elapsed_s"),
                        "text_ready_elapsed_s": turn.get("text_ready_elapsed_s"),
                        "image_ready_elapsed_s": turn.get("image_ready_elapsed_s"),
                        "failure_bucket": turn.get("failure_bucket"),
                        "scene_image_local_path": local_copy or "",
                        "scene_image_url": image_url or "",
                    }
                )

        item_manifest = {
            "benchmark_id": run.get("benchmark_id"),
            "theme_id": run.get("theme_id"),
            "theme": run.get("theme"),
            "game_id": (run.get("worldview") or {}).get("response_json", {}).get("globalState", {}).get("game_id"),
            "selected_option_indices": run.get("selected_option_indices") or [],
            "avg_generation_speed_s": run.get("avg_generation_speed_s"),
            "success": bool(run.get("success")),
            "turns": turn_manifests,
        }
        (item_dir / "item_manifest.json").write_text(
            json.dumps(item_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rows.append(
            {
                "benchmark_id": run.get("benchmark_id"),
                "theme_id": run.get("theme_id"),
                "theme": run.get("theme"),
                "success": bool(run.get("success")),
                "avg_generation_speed_s": run.get("avg_generation_speed_s"),
                "selected_option_indices": json.dumps(run.get("selected_option_indices") or [], ensure_ascii=False),
                "item_manifest_path": str(item_dir / "item_manifest.json"),
            }
        )

    dataset_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(rows),
        "summary": payload.get("summary") or {},
        "items": rows,
    }
    (out_root / "dataset_manifest.json").write_text(
        json.dumps(dataset_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out_root / "dataset_manifest.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["benchmark_id"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    (out_root / "latency_summary.json").write_text(
        json.dumps(payload.get("summary") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out_root / "latency_summary.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        summary = payload.get("summary") or {}
        flat_row = {
            "pregen_depth": summary.get("pregen_depth"),
            "sample_size": summary.get("sample_size"),
            "turn_count": summary.get("turn_count"),
            "read_wait_s": summary.get("read_wait_s"),
            "avg_generation_speed_s": summary.get("avg_generation_speed_s"),
            "turn2_full_ready_mean_s": summary.get("turn2_full_ready_mean_s"),
            "turn3_full_ready_mean_s": summary.get("turn3_full_ready_mean_s"),
            "turn4_full_ready_mean_s": summary.get("turn4_full_ready_mean_s"),
            "strict_success_count": summary.get("strict_success_count"),
            "strict_success_rate": summary.get("strict_success_rate"),
            "placeholder_rate": summary.get("placeholder_rate"),
            "direct_image_rate": summary.get("direct_image_rate"),
            "async_image_rate": summary.get("async_image_rate"),
            "provider_429_count": summary.get("provider_429_count"),
            "provider_timeout_count": summary.get("provider_timeout_count"),
        }
        writer = csv.DictWriter(fh, fieldnames=list(flat_row.keys()))
        writer.writeheader()
        writer.writerow(flat_row)

    with (out_root / "turn_latency_records.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        if item_rows:
            writer = csv.DictWriter(fh, fieldnames=list(item_rows[0].keys()))
            writer.writeheader()
            writer.writerows(item_rows)
        else:
            writer = csv.writer(fh)
            writer.writerow(["benchmark_id", "turn_index", "strict_success", "full_ready_elapsed_s"])

    return dataset_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True, help="Raw benchmark json filename under standard_runs")
    parser.add_argument("--read-wait", type=float, default=60.0)
    parser.add_argument("--pregen-depth", type=int, required=True)
    parser.add_argument("--turn-count", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--image-timeout", type=float, default=60.0)
    parser.add_argument("--image-poll-interval", type=float, default=1.5)
    parser.add_argument("--first-click-timeout", type=int, default=180)
    parser.add_argument("--turn-click-timeout", type=int, default=180)
    parser.add_argument("--profile", default="pregen_depth_fixed_path")
    parser.add_argument("--notes", default="")
    parser.add_argument("--benchmark-file", default=str(REPO_ROOT / "baselines" / "subsets" / "dn_style_formal20.json"))
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET_ROOT))
    parser.add_argument("--dataset-pack-name", default=None)
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark_file)
    if benchmark_path.exists():
        items = load_items_from_file(benchmark_path, limit=args.limit, offset=args.offset)
    else:
        items = load_benchmark(limit=args.limit, offset=args.offset)

    payload = run_depth_suite(
        name=args.name,
        items=items,
        base_url=args.base_url.rstrip("/"),
        read_wait_s=args.read_wait,
        pregen_depth=args.pregen_depth,
        turn_count=args.turn_count,
        profile=args.profile,
        image_timeout_s=args.image_timeout,
        image_poll_interval_s=args.image_poll_interval,
        first_click_timeout_s=args.first_click_timeout,
        turn_click_timeout_s=args.turn_click_timeout,
        notes=args.notes or None,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    default_pack_name = f"depth_{int(args.pregen_depth)}_formal{len(items)}"
    dataset_pack_name = args.dataset_pack_name or default_pack_name
    dataset_root = Path(args.dataset_root) / dataset_pack_name
    export_dataset_pack(payload=payload, out_root=dataset_root)

    print(out_path)
    print(dataset_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

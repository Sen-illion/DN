from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _summary_block(run_payload: dict[str, Any]) -> dict[str, Any]:
    summary = run_payload.get("summary") or {}
    return {
        "profile": summary.get("profile", "default"),
        "sample_size": summary.get("sample_size", 0),
        "transport_success_count": summary.get("transport_success_count", summary.get("success_count", 0)),
        "strict_success_count": summary.get("strict_success_count", summary.get("success_count", 0)),
        "success_count": summary.get("success_count", 0),
        "success_rate": round(
            (summary.get("success_count", 0) / summary.get("sample_size", 1)) if summary.get("sample_size") else 0.0,
            3,
        ),
        "text_ready_elapsed_s": summary.get("text_ready_elapsed_s") or {"count": 0},
        "image_ready_elapsed_s": summary.get("image_ready_elapsed_s") or {"count": 0},
        "full_ready_elapsed_s": summary.get("full_ready_elapsed_s") or {"count": 0},
        "real_scene_rate": summary.get("real_scene_rate"),
        "likely_hit_rate": summary.get("likely_hit_rate"),
        "direct_image_count": summary.get("direct_image_count", 0),
        "async_image_count": summary.get("async_image_count", 0),
        "placeholder_count": summary.get("placeholder_count", 0),
        "placeholder_rate": summary.get("placeholder_rate"),
        "direct_image_rate": summary.get("direct_image_rate"),
        "async_image_rate": summary.get("async_image_rate"),
        "provider_retry_heavy_count": summary.get("provider_retry_heavy_count", 0),
        "provider_429_count": summary.get("provider_429_count", 0),
        "provider_timeout_count": summary.get("provider_timeout_count", 0),
        "provider_backoff_wait_ms_total": summary.get("provider_backoff_wait_ms_total", 0),
        "main_character_contention_suspected_count": summary.get("main_character_contention_suspected_count", 0),
        "failure_bucket_counts": summary.get("failure_bucket_counts") or {},
        "placeholder_strict_fail_count": summary.get("placeholder_strict_fail_count", 0),
        "cache_hit_reason_counts": summary.get("cache_hit_reason_counts") or {},
        "cache_miss_reason_counts": summary.get("cache_miss_reason_counts") or {},
        "global_state_key_drift_detected_count": summary.get("global_state_key_drift_detected_count", 0),
        "scene_id_mismatch_detected_count": summary.get("scene_id_mismatch_detected_count", 0),
        "selected_option_mismatch_detected_count": summary.get("selected_option_mismatch_detected_count", 0),
        "read_wait_s": summary.get("read_wait_s"),
        "notes": summary.get("notes", ""),
    }


def _run_table_rows(label: str, run_payload: dict[str, Any], evidence_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in run_payload.get("runs") or []:
        full = run.get("full_ready") or {}
        rows.append(
            {
                "profile": label,
                "benchmark_id": run.get("benchmark_id"),
                "theme": run.get("theme"),
                "transport_success": bool(run.get("transport_success")),
                "strict_success": bool(run.get("strict_success")),
                "success": bool(run.get("success")),
                "failure_bucket": run.get("failure_bucket"),
                "placeholder": bool(run.get("placeholder")),
                "cache_path_classification": run.get("cache_path_classification"),
                "cache_hit_reason": run.get("cache_hit_reason"),
                "cache_miss_reason": run.get("cache_miss_reason"),
                "global_state_key_drift_detected": bool(run.get("global_state_key_drift_detected")),
                "scene_id_mismatch_detected": bool(run.get("scene_id_mismatch_detected")),
                "selected_option_mismatch_detected": bool(run.get("selected_option_mismatch_detected")),
                "text_ready_elapsed_s": full.get("text_ready_elapsed_s"),
                "image_ready_elapsed_s": full.get("image_ready_elapsed_s"),
                "full_ready_elapsed_s": full.get("full_ready_elapsed_s"),
                "ready_mode": full.get("ready_mode"),
                "second_click_status": (run.get("second_click") or {}).get("status"),
                "second_click_placeholder": (run.get("second_click") or {}).get("is_placeholder"),
                "provider_429_count": (full.get("attribution") or {}).get("provider_429_count"),
                "provider_timeout_count": (full.get("attribution") or {}).get("provider_timeout_count"),
                "provider_retry_heavy_count": (full.get("attribution") or {}).get("provider_retry_heavy_count"),
                "provider_backoff_wait_ms_total": (full.get("attribution") or {}).get("provider_backoff_wait_ms_total"),
                "main_character_event_count": (full.get("attribution") or {}).get("main_character_event_count"),
                "main_character_contention_suspected": (full.get("attribution") or {}).get("main_character_contention_suspected"),
                "image_probe_attempt_count": (full.get("attribution") or {}).get("image_probe_attempt_count"),
                "evidence_path": str(evidence_path),
            }
        )
    return rows


def build_strict_rows(
    dn_run_path: Path,
    dn_summary: dict[str, Any],
    first_turn_csv: Path,
    next_turn_csv: Path,
) -> list[dict[str, Any]]:
    first_turn_rows = {row["baseline"]: row for row in load_csv_rows(first_turn_csv)}
    next_turn_rows = {row["baseline"]: row for row in load_csv_rows(next_turn_csv)}

    strict_rows = [
        {
            "system": "DN",
            "group": "strict_fullready",
            "sample_size": dn_summary["sample_size"],
            "first_turn_or_first_ready_mean_s": "",
            "next_turn_full_ready_mean_s": dn_summary["full_ready_elapsed_s"].get("mean"),
            "p95_s": dn_summary["full_ready_elapsed_s"].get("p95"),
            "success_rate": dn_summary["success_rate"],
            "output_dir_or_evidence_path": str(dn_run_path),
            "notes": (
                "DN row measures click-to-text+image full-ready latency on 20 items with zero dwell time before the "
                "second click; strict v2 also tracks placeholder rate, direct image rate, and provider-side long-tail signals."
            ),
        }
    ]

    for baseline in ("storydiffusion", "sdmv2", "ic-lora"):
        first_row = first_turn_rows[baseline]
        next_row = next_turn_rows[baseline]
        strict_rows.append(
            {
                "system": baseline,
                "group": "image_baseline_reference",
                "sample_size": int(next_row["sample_size"]),
                "first_turn_or_first_ready_mean_s": float(first_row["mean_latency_s"]),
                "next_turn_full_ready_mean_s": float(next_row["next_turn_time_mean_s"] or next_row["mean_latency_s"]),
                "p95_s": float(next_row["next_turn_p95_s"] or next_row["p95_latency_s"]),
                "success_rate": float(next_row["success_rate"]),
                "output_dir_or_evidence_path": next_row["output_dir"],
                "notes": next_row["notes"],
            }
        )
    return strict_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-run", required=True)
    parser.add_argument("--pregen-run", required=True)
    parser.add_argument("--first-turn-csv", required=True)
    parser.add_argument("--next-turn-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--per-item-csv", required=True)
    parser.add_argument("--strict-main-csv", required=True)
    args = parser.parse_args()

    normal_run_path = Path(args.normal_run)
    pregen_run_path = Path(args.pregen_run)
    normal_payload = load_json(normal_run_path)
    pregen_payload = load_json(pregen_run_path)

    summary_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profiles": {
            "normal20": {
                "evidence_path": str(normal_run_path),
                **_summary_block(normal_payload),
            },
            "pregen60s20": {
                "evidence_path": str(pregen_run_path),
                **_summary_block(pregen_payload),
            },
        },
        "notes": [
            "normal20 is intended for strict comparison against the formal20 image-baseline next-turn rows.",
            "pregen60s20 keeps the same 20 benchmark items but simulates a 60-second player read interval to expose pregeneration benefit.",
            "StoryDiffusion / SDM-v2 / IC-LoRA rows in the strict table continue to use their existing formal20 next-turn image-continuation results.",
        ],
    }

    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    table_rows = _run_table_rows("normal20", normal_payload, normal_run_path)
    table_rows.extend(_run_table_rows("pregen60s20", pregen_payload, pregen_run_path))
    write_csv(Path(args.per_item_csv), table_rows)

    strict_rows = build_strict_rows(
        dn_run_path=normal_run_path,
        dn_summary=summary_payload["profiles"]["normal20"],
        first_turn_csv=Path(args.first_turn_csv),
        next_turn_csv=Path(args.next_turn_csv),
    )
    write_csv(Path(args.strict_main_csv), strict_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

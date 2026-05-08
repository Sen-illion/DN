from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1", required=True)
    parser.add_argument("--d2", required=True)
    parser.add_argument("--d3", required=True)
    parser.add_argument("--d4", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--table-csv", required=True)
    parser.add_argument("--paper-table-csv", required=True)
    args = parser.parse_args()

    run_paths = {
        1: Path(args.d1),
        2: Path(args.d2),
        3: Path(args.d3),
        4: Path(args.d4),
    }

    runs: dict[int, dict[str, Any]] = {}
    table_rows: list[dict[str, Any]] = []
    paper_rows: list[dict[str, Any]] = []

    for depth in (1, 2, 3, 4):
        payload = load_json(run_paths[depth])
        summary = payload.get("summary") or {}
        runs[depth] = summary
        table_rows.append(
            {
                "pregeneration_rounds": depth,
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
                "provider_retry_heavy_count": summary.get("provider_retry_heavy_count"),
                "evidence_path": str(run_paths[depth]),
                "notes": summary.get("notes", ""),
            }
        )
        paper_rows.append(
            {
                "pregeneration_rounds": depth,
                "avg_generation_speed_s": summary.get("avg_generation_speed_s"),
                "text_consistency": "pending_eval_from_dataset",
                "image_consistency": "pending_eval_from_dataset",
                "notes": "fixed_path depth ablation on formal20; metric is mean full-ready latency of turn2-4",
            }
        )

    summary_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_paths": {str(k): str(v) for k, v in run_paths.items()},
        "depth_summaries": {str(k): runs[k] for k in (1, 2, 3, 4)},
        "table_rows": table_rows,
        "paper_table_rows": paper_rows,
    }

    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(Path(args.table_csv), table_rows)
    write_csv(Path(args.paper_table_csv), paper_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Aggregate image baseline run directories into comparison tables."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from baseline_io import load_json, write_json


FIELDS = [
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


def infer_mode(metrics: dict) -> str | None:
    mode = metrics.get("mode")
    if mode:
        return mode
    if (
        metrics.get("next_turn_time_mean_s") is not None
        or metrics.get("next_turn_p95_s") is not None
        or metrics.get("continuation_success_rate") is not None
    ):
        return "next_turn"
    return "first_turn"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+", help="Run directories containing metrics.json.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    args = parser.parse_args()

    rows = []
    for run_dir in args.run_dirs:
        metrics_path = Path(run_dir) / "metrics.json"
        metrics = load_json(metrics_path)
        row = {field: metrics.get(field) for field in FIELDS}
        row["mode"] = infer_mode(metrics)
        row["failed_ids"] = ";".join(str(x) for x in metrics.get("failed_ids", []))
        rows.append(row)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_json(output.with_suffix(".json"), rows)
    print(output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarize DN human ratings.

Input is a CSV following templates/human_rating_template_v1.csv.
Outputs a JSON summary and optional CSV with per-sample aggregates.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

TEXT_METRICS = ["text_coherence_1to5"]
IMAGE_METRICS = [
    "overall_score",
    "semantic_consistency",
    "subject_attribute_consistency",
    "spatial_consistency",
    "style_lighting_consistency",
    "detail_integrity",
]
ALL_METRICS = TEXT_METRICS + IMAGE_METRICS


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(number)


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": round(mean(values), 4),
        "median": round(median(values), 4),
        "std": round(pstdev(values), 4) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def needs_adjudication(rows: list[dict[str, str]], metric_names: list[str]) -> bool:
    if len(rows) < 2:
        return False
    for metric in metric_names:
        values = [v for row in rows if (v := parse_float(row.get(metric))) is not None]
        if values and max(values) - min(values) >= 2:
            return True
    disq = [parse_int(row.get("disqualifying_defect_0or1")) == 1 for row in rows]
    overall = [parse_float(row.get("overall_score")) for row in rows]
    if any(disq) and any(v is not None and v >= 4 for v in overall):
        return True
    confidences = [parse_float(row.get("confidence")) for row in rows]
    scores = [parse_float(row.get("overall_score")) for row in rows]
    pairs = [(s, c) for s, c in zip(scores, confidences) if s is not None and c is not None and c > 0]
    if len(pairs) >= 2:
        plain = mean(s for s, _ in pairs)
        weighted = sum(s * c for s, c in pairs) / sum(c for _, c in pairs)
        if abs(weighted - plain) >= 0.35:
            return True
    return False


def summarize(rows: list[dict[str, str]], pass_threshold: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_sample: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_rater: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_sample[row.get("sample_id", "")].append(row)
        by_rater[row.get("rater_id", "")].append(row)

    metric_summary = {metric: stats([v for row in rows if (v := parse_float(row.get(metric))) is not None]) for metric in ALL_METRICS}

    sample_rows: list[dict[str, Any]] = []
    adjudication_count = 0
    pass_count = 0
    scored_count = 0
    for sample_id, sample_ratings in sorted(by_sample.items()):
        modality = sample_ratings[0].get("modality", "") if sample_ratings else ""
        metrics = TEXT_METRICS if modality == "text" else IMAGE_METRICS
        adjudication = needs_adjudication(sample_ratings, metrics)
        adjudication_count += int(adjudication)
        aggregate: dict[str, Any] = {
            "sample_id": sample_id,
            "modality": modality,
            "rater_count": len({r.get("rater_id", "") for r in sample_ratings}),
            "adjudication_needed": int(adjudication),
            "any_disqualifying_defect": int(any(parse_int(r.get("disqualifying_defect_0or1")) == 1 for r in sample_ratings)),
        }
        for metric in metrics:
            values = [v for r in sample_ratings if (v := parse_float(r.get(metric))) is not None]
            aggregate[f"{metric}_mean"] = round(mean(values), 4) if values else None
            aggregate[f"{metric}_min"] = min(values) if values else None
            aggregate[f"{metric}_max"] = max(values) if values else None
        primary = "text_coherence_1to5" if modality == "text" else "overall_score"
        primary_mean = aggregate.get(f"{primary}_mean")
        if primary_mean is not None:
            scored_count += 1
            passed = primary_mean >= pass_threshold and aggregate["any_disqualifying_defect"] == 0
            pass_count += int(passed)
            aggregate["pass_0or1"] = int(passed)
        else:
            aggregate["pass_0or1"] = None
        sample_rows.append(aggregate)

    rater_summary = {}
    for rater_id, rater_rows in sorted(by_rater.items()):
        rater_summary[rater_id] = {
            metric: stats([v for row in rater_rows if (v := parse_float(row.get(metric))) is not None])
            for metric in ALL_METRICS
        }

    summary = {
        "row_count": len(rows),
        "sample_count": len(by_sample),
        "rater_count": len(by_rater),
        "pass_threshold": pass_threshold,
        "pass_rate": round(pass_count / scored_count, 4) if scored_count else None,
        "adjudication_rate": round(adjudication_count / len(by_sample), 4) if by_sample else None,
        "metrics": metric_summary,
        "raters": rater_summary,
    }
    return summary, sample_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize DN human evaluation ratings.")
    parser.add_argument("--input", required=True, help="Input human ratings CSV")
    parser.add_argument("--output-json", required=True, help="Output summary JSON")
    parser.add_argument("--output-samples-csv", help="Optional per-sample aggregate CSV")
    parser.add_argument("--pass-threshold", type=float, default=4.0)
    args = parser.parse_args()

    input_path = Path(args.input)
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    summary, sample_rows = summarize(rows, args.pass_threshold)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.output_samples_csv:
        output_csv = Path(args.output_samples_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = sorted({key for row in sample_rows for key in row.keys()})
        with output_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_rows)

    print(json.dumps({"summary": str(output_json), "samples_csv": args.output_samples_csv}, ensure_ascii=False))


if __name__ == "__main__":
    main()

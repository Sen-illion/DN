from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_any(text: str | None, phrases: list[str]) -> bool:
    if not text:
        return False
    return any(p in text for p in phrases)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 3)
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * q
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(sorted_values[lower], 3)
    weight = rank - lower
    interpolated = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    return round(interpolated, 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="genagents_consistency_2026-04-25_pending.json")
    parser.add_argument("--output-json", default="genagents_consistency_summary_2026-04-25.json")
    parser.add_argument("--output-csv", default="genagents_consistency_per_item_2026-04-25.csv")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    raw_path = baseline_root / "raw_runs" / args.input
    payload = load_json(raw_path)

    rows = []
    turn_success_total = 0
    turn_total = 0
    must_hit_total = 0
    must_total = 0
    forbidden_violations = 0
    latency_values = []

    for run in payload.get("runs", []):
        joined = "\n".join((t.get("response") or "") for t in run.get("turn_outputs", []))
        turn_success = sum(1 for t in run.get("turn_outputs", []) if t.get("success"))
        for t in run.get("turn_outputs", []):
            turn_total += 1
            if t.get("success"):
                turn_success_total += 1
            if isinstance(t.get("latency_s"), (int, float)):
                latency_values.append(float(t["latency_s"]))

        must_hits = sum(1 for m in run.get("must_have_constraints", []) if contains_any(joined, [m[:8], m[:6]]))
        forbidden_hits = sum(1 for f in run.get("forbidden_issues", []) if contains_any(joined, [f[:8], f[:6]]))
        must_hit_total += must_hits
        must_total += len(run.get("must_have_constraints", []))
        forbidden_violations += forbidden_hits

        rows.append(
            {
                "benchmark_id": run["benchmark_id"],
                "theme": run["theme"],
                "turn_count": run["turn_count"],
                "successful_turns": turn_success,
                "all_turns_success": run["all_turns_success"],
                "must_constraint_count": len(run.get("must_have_constraints", [])),
                "must_constraint_hits_heuristic": must_hits,
                "forbidden_issue_count": len(run.get("forbidden_issues", [])),
                "forbidden_hits_heuristic": forbidden_hits,
                "focus": run.get("focus"),
            }
        )

    summary = {
        "baseline": "genagents",
        "run_id": payload.get("run_id"),
        "benchmark_set": payload.get("subset", {}).get("subset_name"),
        "sample_size": payload.get("summary", {}).get("sample_size"),
        "turn_total": turn_total,
        "turn_success_rate": round(turn_success_total / turn_total, 3) if turn_total else 0.0,
        "item_full_success_rate": payload.get("summary", {}).get("full_success_rate"),
        "must_constraint_hit_rate_heuristic": round(must_hit_total / must_total, 3) if must_total else 0.0,
        "forbidden_violation_rate_heuristic": round(forbidden_violations / turn_total, 3) if turn_total else 0.0,
        "latency_mean_s": round(sum(latency_values) / len(latency_values), 3) if latency_values else None,
        "latency_p95_s": percentile(latency_values, 0.95),
        "credential_blocked": payload.get("summary", {}).get("credential_blocked", False),
        "notes": [
            "Heuristic hit-rate is only a placeholder until live runs and stronger evaluators are added.",
            "This summary is intended to support scaffold table updates and protocol debugging.",
        ],
    }

    summary_path = baseline_root / "summaries" / args.output_json
    csv_path = baseline_root / "summaries" / args.output_csv
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["benchmark_id"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    print(f"Wrote summary json to: {summary_path}")
    print(f"Wrote per-item csv to: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

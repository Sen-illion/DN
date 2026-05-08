from __future__ import annotations

import csv
import json
import math
from pathlib import Path


TARGET_IDS = [
    "DNQBV1_001",
    "DNQBV1_002",
    "DNQBV1_004",
    "DNQBV1_005",
    "DNQBV1_007",
    "DNQBV1_009",
    "DNQBV1_013",
    "DNQBV1_018",
]


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
    value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
    return round(value, 3)


def main() -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[4]
    worldview_run_path = (
        repo_root
        / "experiments"
        / "benchmark"
        / "standard_runs"
        / "benchmark_v1_worldview_default_20.json"
    )
    out_path = script_path.parent / "dn_table2_row_2026-04-26_genagents_subset_v2.csv"

    payload = json.loads(worldview_run_path.read_text(encoding="utf-8"))
    runs = payload.get("runs", [])
    subset_runs = [run for run in runs if run.get("benchmark_id") in TARGET_IDS]
    elapsed_values = [float(run["elapsed_s"]) for run in subset_runs if isinstance(run.get("elapsed_s"), (int, float))]
    success_count = sum(1 for run in subset_runs if run.get("status") == "success")

    row = {
        "system": "DN",
        "baseline_role": "ours",
        "comparison_scope": "worldview planning on matched GenAgents subset",
        "benchmark_set": "benchmark_v1_worldview_default_genagents_subset_v2_8",
        "sample_size": len(subset_runs),
        "success_rate": round(success_count / len(subset_runs), 3) if subset_runs else 0.0,
        "latency_mean_s": round(sum(elapsed_values) / len(elapsed_values), 3) if elapsed_values else None,
        "latency_p95_s": percentile(elapsed_values, 0.95),
        "persona_consistency": "N/A for DN worldview-only row",
        "setting_adherence": "strong by design; see DN worldview outputs",
        "coherence_score": "N/A for single-shot worldview row",
        "status": "ready",
        "evidence_path": "experiments/benchmark/standard_runs/benchmark_v1_worldview_default_20.json",
        "notes": "DN row recomputed on the same 8 benchmark IDs used by GenAgents subset_v2 for tighter Table 2 comparison.",
    }

    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)

    print(f"Wrote DN subset row to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

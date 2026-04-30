from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", default="genagents_consistency_summary_2026-04-25.json")
    parser.add_argument("--output", default="genagents_table2_row_2026-04-25.csv")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    repo_root = script_path.parents[6]
    summary = load_json(baseline_root / "summaries" / args.summary)
    out_path = repo_root / "experiments" / "paper_method_view" / "2_table2_text_planning" / "summary_tables" / args.output
    judged_metrics = summary.get("judged_metrics", {})

    persona_consistency = judged_metrics.get("persona_consistency_mean_1to5", "TBD after live judge or human eval")
    setting_adherence = summary.get("must_constraint_hit_rate_heuristic")
    coherence_score = "TBD after live judge or human eval"
    notes = "Auto-exported from GenAgents summary script."

    if judged_metrics:
        setting_adherence = judged_metrics.get("setting_adherence_mean_1to5")
        coherence_score = judged_metrics.get("multi_turn_coherence_mean_1to5")
        notes = (
            f"Judge model: {summary.get('judge_model')}; "
            f"theme_alignment_mean_1to5={judged_metrics.get('theme_alignment_mean_1to5')}; "
            f"actionability_mean_1to5={judged_metrics.get('actionability_mean_1to5')}."
        )

    row = {
        "system": "GenAgents",
        "baseline_role": "main baseline",
        "comparison_scope": "persona-conditioned response / state consistency",
        "benchmark_set": summary.get("benchmark_set", "genagents_consistency_subset_v1"),
        "sample_size": summary.get("sample_size"),
        "success_rate": summary.get("item_full_success_rate"),
        "latency_mean_s": summary.get("latency_mean_s"),
        "latency_p95_s": summary.get("latency_p95_s", "TBD"),
        "persona_consistency": persona_consistency,
        "setting_adherence": setting_adherence,
        "coherence_score": coherence_score,
        "status": "credential-blocked" if summary.get("credential_blocked") else "scored",
        "evidence_path": f"experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/{args.summary}",
        "notes": notes,
    }

    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)

    print(f"Wrote table2 row csv to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

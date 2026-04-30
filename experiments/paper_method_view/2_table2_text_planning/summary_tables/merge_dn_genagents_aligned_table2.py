from __future__ import annotations

import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    script_path = Path(__file__).resolve()
    summary_dir = script_path.parent
    dn_row_path = summary_dir / "dn_table2_row_2026-04-26_genagents_subset_v2.csv"
    gen_row_path = summary_dir / "genagents_table2_row_2026-04-26_dn_env_subset_v2.csv"
    out_path = summary_dir / "text_baseline_comparison_aligned_2026-04-26_subset_v2.csv"

    dn_rows = read_csv(dn_row_path)
    gen_rows = read_csv(gen_row_path)
    if not dn_rows or not gen_rows:
        raise RuntimeError("Aligned merge inputs are empty")

    aidungeon_row = {
        "system": "AIDungeon",
        "baseline_role": "supplementary candidate",
        "comparison_scope": "open-ended story continuation",
        "benchmark_set": "TBD adapted subset",
        "sample_size": "TBD",
        "success_rate": "N/A",
        "latency_mean_s": "N/A",
        "latency_p95_s": "N/A",
        "persona_consistency": "TBD",
        "setting_adherence": "TBD",
        "coherence_score": "TBD",
        "status": "runtime-high-risk",
        "evidence_path": "experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_aidungeon/protocol/aidungeon_revival_decision_2026-04-26.md",
        "notes": "No-go for current main experiment cycle; kept only as deferred task-form baseline.",
    }

    rows = [dn_rows[0], gen_rows[0], aidungeon_row]
    write_csv(out_path, rows, list(rows[0].keys()))
    print(f"Wrote aligned table2 csv to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

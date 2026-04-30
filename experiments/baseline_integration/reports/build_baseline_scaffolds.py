from __future__ import annotations

import csv
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[3]

    dn_summary = load_json(repo_root / "experiments" / "benchmark" / "outputs" / "benchmark_v1_summary_metrics.json")
    genagents_smoke = load_json(
        repo_root
        / "experiments"
        / "paper_method_view"
        / "1_table1_main_visual_efficiency"
        / "baselines"
        / "baseline_genagents"
        / "raw_runs"
        / "genagents_smoke_2026-04-25.json"
    )

    table1_rows = [
        {
            "system": "DN",
            "baseline_role": "ours",
            "comparison_scope": "full interactive multimodal system",
            "benchmark_set": "DN-quality-benchmark-v1",
            "sample_size": dn_summary["fullchain_default_summary"]["sample_size"],
            "success_rate": round(
                dn_summary["fullchain_default_summary"]["full_success_count"]
                / dn_summary["fullchain_default_summary"]["sample_size"],
                3,
            ),
            "worldview_mean_s": dn_summary["fullchain_default_summary"]["worldview_elapsed_s"]["mean"],
            "worldview_p95_s": dn_summary["fullchain_default_summary"]["worldview_elapsed_s"]["p95"],
            "first_scene_mean_s": dn_summary["fullchain_default_summary"]["generate_option_elapsed_s"]["mean"],
            "first_scene_p95_s": dn_summary["fullchain_default_summary"]["generate_option_elapsed_s"]["p95"],
            "visual_support": "yes",
            "status": "ready",
            "evidence_path": "experiments/benchmark/outputs/benchmark_v1_summary_metrics.json",
            "notes": "Current DN reference row.",
        },
        {
            "system": "GenAgents",
            "baseline_role": "main baseline",
            "comparison_scope": "text planning / state consistency",
            "benchmark_set": genagents_smoke["benchmark_subset"]["benchmark_source"],
            "sample_size": genagents_smoke["benchmark_subset"]["sample_size"],
            "success_rate": "N/A",
            "worldview_mean_s": "N/A",
            "worldview_p95_s": "N/A",
            "first_scene_mean_s": "N/A",
            "first_scene_p95_s": "N/A",
            "visual_support": "no",
            "status": "integration-ready, credential-blocked",
            "evidence_path": "experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/raw_runs/genagents_smoke_2026-04-25.json",
            "notes": "Public sample agent load passed; live inference pending OPENAI_API_KEY.",
        },
        {
            "system": "StoryDiffusion",
            "baseline_role": "supplementary baseline",
            "comparison_scope": "visual consistency subtask",
            "benchmark_set": "storydiffusion_visual_subset_v1",
            "sample_size": 6,
            "success_rate": "N/A",
            "worldview_mean_s": "N/A",
            "worldview_p95_s": "N/A",
            "first_scene_mean_s": "N/A",
            "first_scene_p95_s": "N/A",
            "visual_support": "yes",
            "status": "blocked on current machine",
            "evidence_path": "experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_storydiffusion/logs/2026-04-25_smoke_test_summary.md",
            "notes": "Needs CUDA-capable machine.",
        },
        {
            "system": "AIDungeon",
            "baseline_role": "main baseline candidate",
            "comparison_scope": "interactive narrative task-shape",
            "benchmark_set": "TBD adapted subset",
            "sample_size": "TBD",
            "success_rate": "N/A",
            "worldview_mean_s": "N/A",
            "worldview_p95_s": "N/A",
            "first_scene_mean_s": "N/A",
            "first_scene_p95_s": "N/A",
            "visual_support": "no",
            "status": "runtime-high-risk",
            "evidence_path": "experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_aidungeon/protocol/aidungeon_runtime_assessment.md",
            "notes": "Legacy TensorFlow/GPT-2 stack.",
        },
    ]

    table2_rows = [
        {
            "system": "DN",
            "baseline_role": "ours",
            "comparison_scope": "worldview planning",
            "benchmark_set": "benchmark_v1_worldview_default_20",
            "sample_size": dn_summary["worldview_default_summary"]["sample_size"],
            "success_rate": round(
                dn_summary["worldview_default_summary"]["success_count"]
                / dn_summary["worldview_default_summary"]["sample_size"],
                3,
            ),
            "latency_mean_s": dn_summary["worldview_default_summary"]["elapsed_s"]["mean"],
            "latency_p95_s": dn_summary["worldview_default_summary"]["elapsed_s"]["p95"],
            "persona_consistency": "TBD",
            "setting_adherence": "TBD",
            "coherence_score": "TBD",
            "status": "ready",
            "evidence_path": "experiments/benchmark/outputs/benchmark_v1_summary_metrics.json",
            "notes": "DN text-planning reference row.",
        },
        {
            "system": "GenAgents",
            "baseline_role": "main baseline",
            "comparison_scope": "persona-conditioned response / state consistency",
            "benchmark_set": genagents_smoke["benchmark_subset"]["subset_name"],
            "sample_size": genagents_smoke["benchmark_subset"]["sample_size"],
            "success_rate": "loader_only",
            "latency_mean_s": genagents_smoke["elapsed_s"],
            "latency_p95_s": "N/A",
            "persona_consistency": "TBD after live runs",
            "setting_adherence": "TBD after live runs",
            "coherence_score": "TBD after live runs",
            "status": "integration-ready, credential-blocked",
            "evidence_path": "experiments/baseline_integration/normalized_runs/genagents_smoke_2026-04-25.normalized.json",
            "notes": "Best next text-side baseline.",
        },
        {
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
            "evidence_path": "experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_aidungeon/protocol/aidungeon_runtime_assessment.md",
            "notes": "Keep as later task-form comparison if revived.",
        },
    ]

    write_csv(
        repo_root
        / "experiments"
        / "paper_method_view"
        / "1_table1_main_visual_efficiency"
        / "summary_tables"
        / "main_baseline_comparison_scaffold_2026-04-25.csv",
        table1_rows,
    )
    write_csv(
        repo_root
        / "experiments"
        / "paper_method_view"
        / "2_table2_text_planning"
        / "summary_tables"
        / "text_baseline_comparison_scaffold_2026-04-25.csv",
        table2_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

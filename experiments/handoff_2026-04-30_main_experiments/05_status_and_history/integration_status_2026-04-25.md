# Baseline Integration Status

## Ready
- DN native benchmark harness already exists under `experiments/benchmark/`
- baseline folder structure exists under `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/`
- StoryDiffusion is documented and environment-checked
- GenAgents has a dedicated environment, mapped smoke subset, and exported smoke raw run
- GenAgents smoke run has been exported into the unified normalized schema
- baseline comparison scaffold CSVs now exist for Table 1 and Table 2
- GenAgents 3-turn consistency runner, summarizer, and Table 2 row exporter now exist and have produced pending artifacts
- GenAgents now runs successfully against DN's existing `.env` provider configuration and has produced a live Table 2 merged scaffold
- GenAgents now also has a judge-based scorer, an 8-item stable subset, a judged live run, and a Table 2-ready merged scaffold candidate
- GenAgents 8-item judged run now also has a normalized unified export and explicit `latency_p95_s`
- DN now also has a matched 8-item aligned Table 2 row for tighter comparison against `genagents_consistency_subset_v2`

## In progress
- per-baseline adapter documentation
- AIDungeon execution viability decision
- source-of-truth freeze for the expanded text-baseline comparison row set
- short paper-facing text-baseline progress report

## Next
1. prefer `text_baseline_comparison_aligned_2026-04-26_subset_v2.csv` for paper-facing Table 2 discussion
2. keep `text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv` as archive scaffold evidence
3. keep `normalized_runs/genagents_consistency_live_2026-04-26_dn_env_subset_v2.normalized.json` as the unified appendix-facing export
4. keep the explicit AIDungeon no-go note in force
5. keep StoryDiffusion deferred on the current machine

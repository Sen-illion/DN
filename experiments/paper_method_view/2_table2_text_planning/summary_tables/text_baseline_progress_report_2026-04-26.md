# Text Baseline Progress Report (2026-04-26)

## Current source of truth
- current comparison CSV:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv`
- recommended paper-facing aligned CSV:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_aligned_2026-04-26_subset_v2.csv`
- current GenAgents evidence row:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-26_dn_env_subset_v2.csv`
- current aligned DN row:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/dn_table2_row_2026-04-26_genagents_subset_v2.csv`
- current judged evidence file:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_judged_live_2026-04-26_dn_env_subset_v2.json`
- paper-ready subsection draft:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/table2_experiment_subsection_zh_2026-04-26.md`

## What was run
- baseline: `GenAgents`
- provider path: DN existing `.env` OpenAI-compatible configuration
- evaluation subset: `genagents_consistency_subset_v2`
- sample size: 8 items
- protocol: fixed 3-turn persona-consistency / state-stability run

## Trustworthy metrics now
- `turn_success_rate = 0.958`
- `item_full_success_rate = 0.875`
- `latency_mean_s = 7.343`
- `latency_p95_s = 11.425`
- judge-based means:
  - `theme_alignment_mean_1to5 = 4.875`
  - `setting_adherence_mean_1to5 = 4.875`
  - `persona_consistency_mean_1to5 = 5.0`
  - `multi_turn_coherence_mean_1to5 = 4.75`
  - `actionability_mean_1to5 = 4.875`
  - `major_error_rate = 0.125`

Why these are trustworthy enough for current paper drafting:
- raw run JSON, per-item CSV, judged CSV, and merged comparison scaffold all exist
- one known failure item is explicitly preserved rather than hidden
- quality metrics are now judge-based rather than keyword-hit placeholders

## Metrics still placeholder or incomplete
- `must_constraint_hit_rate_heuristic` remains `0.0` and should not be used as final paper evidence
- `forbidden_violation_rate_heuristic` is still only a placeholder diagnostic
- no human rating pass has been completed for the expanded subset
- no direct multimodal comparison is available because GenAgents does not produce DN-style worldview JSON, branch options, or images

## Safe claims for the paper
- GenAgents is now a genuinely runnable external text baseline, not just an integrated repository
- Under DN's current test API path, GenAgents shows high persona consistency and strong multi-turn coherence on the 8-item text subset
- GenAgents can support Table 2 as a text planning / state consistency baseline
- the paper-facing comparison should prefer the aligned 8-item DN row over the older 20-item DN summary row
- GenAgents should not be framed as a full baseline for DN's multimodal interactive loop
- The current main quantitative weakness is run reliability on a minority of items, with `DNQBV1_009` showing one blocked turn

## Unsafe claims to avoid
- do not claim GenAgents matches DN on image generation or text-image coordination
- do not cite heuristic constraint-hit values as quality evidence
- do not present judge-based scores as human gold labels
- do not say AIDungeon or StoryDiffusion are completed baselines

## Immediate next recommended action
1. keep `text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv` as the current Table 2 source of truth
2. for the main paper table, prefer `text_baseline_comparison_aligned_2026-04-26_subset_v2.csv`
3. keep `experiments/baseline_integration/normalized_runs/genagents_consistency_live_2026-04-26_dn_env_subset_v2.normalized.json` as the appendix-facing unified export
4. only after freezing this text-baseline package, keep AIDungeon as no-go and StoryDiffusion as deferred

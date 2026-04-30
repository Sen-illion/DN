# Main Experiment Narrative Integration (2026-04-26)

## Purpose

This note turns the current `paper_method_view` materials into one coherent experiment story for the paper-facing main experiment.

It is not just a file inventory. It answers:

- what the current main experiment is actually comparing
- which external baselines are now frozen into the core main table
- why `WorldGeneration` is only supplementary
- what DN can claim safely
- which files should now be treated as source of truth

---

## 1. Recommended experiment storyline

The current main experiment should be framed as a three-part story:

1. `DN native complete-system evidence`
   - show that DN runs end-to-end reliably on the internal benchmark
   - support this with worldview/fullchain efficiency and completion summaries

2. `External playable-latency baseline comparison`
   - show that DN is not only evaluated in isolation
   - compare DN with runnable external systems under one unified playable-latency protocol
   - keep the comparison explicitly defined as an external system-shape comparison, not a fully isomorphic competition

3. `Component ablations`
   - show which internal modules matter
   - use pregeneration, council, and readwait results to explain why DN reaches its current latency and interaction profile

This is now stronger and cleaner than mixing baseline hunting, parameter studies, and all auxiliary tables into one large narrative.

---

## 2. Frozen main-table structure

The core main table is now frozen as:

1. `DN`
2. `LIGHT`
3. `Plan-Write-Revise`
4. `GenAgents`

The supplementary comparison row is fixed as:

- `WorldGeneration`

This role split must remain explicit:

- `DN` = complete system row
- `LIGHT` = preferred authoritative external row
- `Plan-Write-Revise` = speed/reference row
- `GenAgents` = continuity supplement row
- `WorldGeneration` = supplementary fallback row

Recommended source files:

- core main table:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- supplementary WorldGeneration row:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`
- source-of-truth writing index:
  - `experiments/paper_method_view/0_overview/main_experiment_writing_bundle_index_2026-04-26.md`

---

## 3. What is already strong enough for the paper

### 3.1 DN native results

The DN side is still the strongest and most complete part of the package.

Key evidence:

- `experiments/paper_method_view/1_table1_main_visual_efficiency/efficiency_metrics/benchmark_v1_summary_metrics.json`
- `experiments/benchmark/outputs/benchmark_v1_summary_metrics.json`

Current strong claims:

- DN `worldview_default_20` reached `20 / 20`
- DN `fullchain_default_20` reached `20 / 20`
- DN fullchain substage latency is traceable:
  - worldview mean `12.458 s`
  - option generation mean `7.662 s`
  - main character completion mean `55.912 s`
- DN has strong guardrail evidence for success rate, image return, option completeness, and low pollution/fallback rates

Interpretation:

- DN can already be described as a stable end-to-end system rather than a demo-only prototype

### 3.2 External baseline evidence

The current paper-facing external baseline package is no longer centered on only one text baseline. It is now a frozen four-row main table plus one supplementary row.

Current strong claims:

- `LIGHT` is runnable and now serves as the most authoritative external main-table row
- `Plan-Write-Revise` is runnable and provides a lightweight speed/reference comparison point
- `GenAgents` is runnable and provides a continuity/state supplement
- `WorldGeneration` is runnable only through a fallback reconstruction path and is therefore supplementary rather than core

Interpretation:

- the paper no longer needs to claim that all baselines are fully equivalent to DN
- instead, it can safely claim that DN now has a runnable external comparison set under a unified playable-latency protocol

### 3.3 Ablation evidence

The ablation block is already rich enough to support mechanism-level claims.

Key evidence:

- pregeneration:
  - `experiments/paper_method_view/4_ablations/pregeneration/benchmark_v3_pregen_clean_ablation_summary.json`
- council:
  - `experiments/paper_method_view/4_ablations/council/benchmark_v1_fullchain_ab_summary.json`
- readwait:
  - `experiments/paper_method_view/4_ablations/readwait/summaries/benchmark_v13_readwait_70s_7v8_cleaned_summary.json`

Current strong claims:

- pregeneration materially changes latency distribution
- council affects both latency and some reliability dimensions
- readwait affects real-scene hit behavior rather than only raw waiting time

Interpretation:

- DN's final configuration is supported by ablation evidence rather than intuition alone

---

## 4. How the core main table should be interpreted

The current main table is not a claim that DN is the fastest among all systems.

Current row meanings are:

- `LIGHT` shows what a more authoritative external interaction/dialogue system looks like under the same playable-latency framing
- `Plan-Write-Revise` shows how fast a lightweight on-demand story generator can be
- `GenAgents` shows what a stateful continuity-oriented system looks like in the same comparison family

This allows the paper to make a safer claim:

- DN should be interpreted as a complete interactive narrative system returning playable content under controlled latency
- the faster `LIGHT` and `Plan-Write-Revise` rows mainly show that lighter text-generation systems have natural speed advantages on short immediate text responses
- the `GenAgents` row shows that even a stronger state-continuity agent system is not automatically better than DN on all latency dimensions

Important caveat:

- the DN row currently uses `fullchain generate_option latency` as the working `first_playable_time_s` proxy
- this is acceptable for the current main experiment, but it must be disclosed as a proxy rather than a stronger full cold-start timing claim

---

## 5. Why WorldGeneration is supplementary only

`WorldGeneration` still has value, but it must stay outside the core main-table conclusion set.

Reason:

- the current runnable path is a fallback reconstruction path
- it is not the full original pipeline described in the paper/system design
- therefore it is weaker than `LIGHT` in authority and reproducibility for the core main table

Safe paper role:

- use it to preserve a world-construction-oriented comparison view
- do not use it as the main winner/loser row in the core conclusion table

---

## 6. Claims that are safe vs unsafe

### Safe claims

- DN is a stable end-to-end system on the current benchmark
- DN now has a frozen runnable external baseline table under a unified playable-latency protocol
- `LIGHT` is the preferred authoritative external row
- `Plan-Write-Revise` is a speed/reference row
- `GenAgents` is a continuity supplement row
- `WorldGeneration` is preserved as a supplementary fallback row
- DN's current method configuration is supported by ablation evidence

### Claims that require qualification

- DN vs external baselines is not a fully isomorphic comparison
- the DN `first_playable_time_s` row is currently proxy-based
- `LIGHT` is more authoritative than semantically faithful to DN's Chinese benchmark themes

### Claims to avoid

- do not say DN is absolutely fastest among all baselines
- do not say `LIGHT` is fully equivalent to DN
- do not say `WorldGeneration` was fully faithfully revived
- do not say current baseline coverage fully spans DN's multimodal system capacity

---

## 7. Source-of-truth writing bundle

If someone drafts the experiment chapter now, the primary bundle should be:

- `experiments/paper_method_view/0_overview/main_experiment_writing_bundle_index_2026-04-26.md`
- `experiments/paper_method_view/0_overview/experiment_section_draft_zh_2026-04-26.md`
- `experiments/paper_method_view/0_overview/main_playable_latency_results_interpretation_zh_2026-04-26.md`
- `experiments/paper_method_view/0_overview/figure_table_caption_pack_zh_2026-04-26.md`
- `experiments/paper_method_view/0_overview/limitations_zh_2026-04-26.md`
- `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`

---

## 8. Bottom line

The current paper package is no longer blocked by lack of runnable external baselines.

The strongest present story is:

- DN already has strong native complete-system evidence
- DN now has a frozen external baseline main table under one unified playable-latency protocol
- `LIGHT` provides the strongest authoritative external row
- `Plan-Write-Revise` and `GenAgents` provide complementary external reference directions
- `WorldGeneration` is retained, but only as supplementary fallback evidence
- DN's key configuration choices are supported by multiple ablations

So the next work should focus on final paper wording and final table packaging, not on reopening baseline membership.

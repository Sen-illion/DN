# DN Main Experiment Next 3-Day Execution Checklist

This checklist is the current execution baseline for the DN main experiment.

Rule:
- do not skip ahead casually
- do not replace this checklist with ad hoc work halfway through
- if a step is blocked, record the blocker explicitly before moving to the next allowed branch

---

## Overall objective

Turn the current DN experiment stack into a paper-ready main experiment package with:
- one runnable external text baseline
- one clear visual supplementary baseline status
- one explicit decision on the legacy interactive baseline
- one traceable set of summary tables and raw-run evidence

---

## Priority order

1. `GenAgents`
2. `AIDungeon`
3. `StoryDiffusion`

Why this order:
- `GenAgents` is already runnable on the current machine and can produce paper-usable external baseline evidence fastest
- `AIDungeon` is task-shape relevant but operationally risky
- `StoryDiffusion` is blocked by current hardware and should not consume main execution time now

---

## Day 1: Finish the first paper-usable GenAgents baseline

### Step 1.1
Confirm the current live artifacts are intact.

Required files:
- `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/raw_runs/genagents_consistency_live_2026-04-26_dn_env.json`
- `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_live_summary_2026-04-26_dn_env.json`
- `experiments/paper_method_view/2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-26_dn_env.csv`
- `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env.csv`

Completion standard:
- files exist
- no broken JSON / CSV
- status remains traceable

### Step 1.2
Replace weak heuristic scoring with a stronger judge-based rubric.

Target:
- add a judge/scorer for:
  - theme alignment
  - persona consistency
  - multi-turn coherence
  - actionability

Expected output:
- `baseline_genagents/summaries/genagents_consistency_judged_*.json`
- `baseline_genagents/summaries/genagents_consistency_judged_*.csv`

Completion standard:
- every live item has a judged score row
- the scoring method is documented

Status update on 2026-04-26:
- completed
- produced:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_judged_live_2026-04-26_dn_env.json`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_judged_live_2026-04-26_dn_env.csv`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/protocol/judge_protocol.md`
- judged means from the current 3-item live run:
  - theme_alignment = 4.667 / 5
  - setting_adherence = 4.667 / 5
  - persona_consistency = 4.667 / 5
  - multi_turn_coherence = 4.0 / 5
  - actionability = 4.667 / 5
  - major_error_rate = 0.333

### Step 1.3
Expand the GenAgents subset beyond 3 items.

Target:
- create a larger Table-2-ready subset
- recommended size: 8 items first, not 20 immediately

Expected new file:
- `baseline_genagents/protocol/genagents_consistency_subset_v2.json`

Selection principle:
- keep genre diversity
- keep theme diversity
- include at least one grounded realistic item
- include at least one sci-fi item
- include at least one suspense item

Completion standard:
- subset committed as a stable evaluation set
- each item has a stated focus

Status update on 2026-04-26:
- completed
- produced:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/protocol/genagents_consistency_subset_v2.json`
- subset size: 8
- covered focus types:
  - grounded realism
  - post-apocalyptic realism
  - institutional sci-fi conflict
  - high-pressure sci-fi survival
  - identity-boundary reasoning
  - classical narration suspense
  - isolated suspense
  - historical investigation

### Step 1.4
Run the expanded GenAgents live experiment.

Expected output:
- new raw run JSON
- new summary JSON
- new per-item CSV
- updated Table 2 row
- updated merged Table 2 scaffold
- updated eval packet

Completion standard:
- at least one expanded live run completes
- summary table can be cited in the paper draft

Status update on 2026-04-26:
- completed
- produced:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/raw_runs/genagents_consistency_live_2026-04-26_dn_env_subset_v2.json`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_live_summary_2026-04-26_dn_env_subset_v2.json`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_live_per_item_2026-04-26_dn_env_subset_v2.csv`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_consistency_judged_live_2026-04-26_dn_env_subset_v2.json`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_eval_packet_live_2026-04-26_dn_env_subset_v2.csv`
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_eval_packet_live_2026-04-26_dn_env_subset_v2.md`
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-26_dn_env_subset_v2.csv`
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv`
- expanded run metrics:
  - sample_size = 8
  - turn_success_rate = 0.958
  - item_full_success_rate = 0.875
  - latency_mean_s = 7.343
  - latency_p95_s = 11.425
  - persona_consistency_mean = 5.0 / 5
  - setting_adherence_mean = 4.875 / 5
  - coherence_mean = 4.75 / 5
  - actionability_mean = 4.875 / 5
  - major_error_rate = 0.125
- known failure carried into record:
  - `DNQBV1_009` had one blocked turn and is the main reason the full-item success rate is below 1.0

---

## Day 2: Consolidate Table 2 and baseline evidence

### Step 2.1
Freeze the Table 2 comparison row set.

Target files:
- `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_merged_*.csv`

Required contents:
- DN row
- GenAgents row
- AIDungeon placeholder or status row if still not runnable

Completion standard:
- one comparison CSV is designated as the current source of truth

Status update on 2026-04-26:
- completed
- archive scaffold:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv`
- recommended paper-facing aligned table:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_aligned_2026-04-26_subset_v2.csv`
- supporting aligned DN row:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/dn_table2_row_2026-04-26_genagents_subset_v2.csv`

### Step 2.2
Generate a short text-baseline report.

Expected file:
- `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_progress_report_2026-04-xx.md`

It should state:
- what was run
- what metric is trustworthy
- what metric is still placeholder
- what claims are safe to make in the paper

Status update on 2026-04-26:
- completed
- produced:
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_progress_report_2026-04-26.md`
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/table2_alignment_note_2026-04-26.md`
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/table2_results_draft_zh_2026-04-26.md`
  - `experiments/paper_method_view/2_table2_text_planning/summary_tables/table2_experiment_subsection_zh_2026-04-26.md`

### Step 2.3
Prepare human or judge review packet for the expanded GenAgents run.

Expected output:
- eval packet CSV
- eval packet Markdown

Completion standard:
- packet can be handed to a rater without extra cleanup

---

## Day 3: Decide the next external baseline branch

### Branch A: AIDungeon revival decision

Do this only after Day 1 and Day 2 are complete.

Task:
- decide whether to invest in reviving the legacy TensorFlow/GPT-2 local stack

Expected output:
- `baseline_aidungeon/protocol/aidungeon_revival_decision_2026-04-xx.md`

Must answer:
- can it be run faithfully on current machine
- if not, what exact blocker prevents it
- is there a reduced text-only path worth trying

Completion standard:
- explicit go / no-go decision

Status update on 2026-04-26:
- completed
- decision: `no-go for current main experiment cycle`
- produced:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_aidungeon/protocol/aidungeon_revival_decision_2026-04-26.md`
- blocker summary:
  - legacy `tensorflow==1.15.2` path
  - GPT-2-era local runtime assumptions
  - low paper-yield / engineering-cost ratio on the current machine

### Branch B: StoryDiffusion deferred execution note

Task:
- keep StoryDiffusion documented as blocked on current machine
- do not spend execution time trying to force it locally

Expected output:
- if needed, update `baseline_storydiffusion/status.md`

Completion standard:
- no ambiguity remains about why it is deferred

Status update on 2026-04-26:
- completed
- decision remains: deferred on current machine
- clarified in:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_storydiffusion/status.md`
- practical meaning:
  - do not spend more current-cycle execution time on local StoryDiffusion forcing
  - only reopen on a CUDA-capable machine

---

## Non-negotiable rules during execution

1. Do not abandon `GenAgents` halfway to chase another baseline unless a blocker is documented.
2. Do not claim a baseline is "finished" when only integration is complete.
3. Do not use weak heuristic scores as final paper evidence without labeling them as provisional.
4. Every new run must produce:
   - raw run
   - summary
   - table row or scaffold update
5. If a run fails, write the failure reason back into the baseline status file the same day.

---

## Current status snapshot on 2026-04-26

- DN native experiments: strong and mostly complete
- GenAgents: runnable, now has an expanded 8-item live run with judge-based scoring and Table 2-ready merged scaffold
- AIDungeon: not yet runnable, decision pending
- StoryDiffusion: blocked on current hardware

---

## Source-of-truth files to keep updated

- `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/status.md`
- `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_aidungeon/status.md`
- `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_storydiffusion/status.md`
- `experiments/baseline_integration/reports/integration_status_2026-04-25.md`
- `experiments/paper_method_view/0_overview/main_experiment_narrative_integration_2026-04-26.md`
- `experiments/paper_method_view/0_overview/experiment_section_draft_zh_2026-04-26.md`
- `experiments/paper_method_view/0_overview/figure_table_caption_pack_zh_2026-04-26.md`
- this checklist file

# Main Playable Latency Progress (2026-04-26)

## What is now in place
- unified playable-latency schema:
  - `experiments/baseline_integration/schema/playable_latency_run_schema.md`
- unified subset files:
  - `experiments/baseline_integration/subsets/efficiency_playable_subset_v1.json`
  - `experiments/baseline_integration/subsets/efficiency_playable_subset_v2.json`
- shared protocol helpers:
  - `experiments/baseline_integration/adapters/playable_protocol.py`
- baseline folder registry:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/README.md`
- execution checklist:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/main_playable_latency_checklist_2026-04-26.md`
- summary builder:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/build_main_playable_latency_table.py`

## Baseline status

### `GenAgents`
- playable-latency conversion completed from the existing 8-item normalized run
- current summary file:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_genagents/summaries/genagents_playable_latency_summary_2026-04-26_subset_v2.json`
- current role:
  - supplementary next-turn / continuity baseline

### `Plan-Write-Revise`
- repo cloned
- official pretrained model pack downloaded
- compatibility patches applied for modern Windows/PyTorch runtime
- 1-item smoke and 5-item playable latency batch both completed
- current summary file:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_plan_write_revise/summaries/pwr_playable_latency_v1_summary_2026-04-26.json`
- current role:
  - runnable speed/reference baseline for on-demand story generation

### `WorldGeneration`
- repo cloned
- baseline folder scaffolded
- graph-to-playable adapter added
- current-cycle fallback runner added:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_worldgeneration/protocol/run_worldgeneration_playable_latency.py`
- 5-item and 8-item playable latency runs completed through the rule-based binary-story fallback path
- current summary file:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_worldgeneration/summaries/worldgeneration_playable_latency_v2_summary_2026-04-26.json`
- current role:
  - supplementary world-construction reference row with explicit fallback-path limitation

### `LIGHT`
- repo cloned:
  - `experiments/external_baselines/LIGHT`
- runnable environment created:
  - `experiments/external_baselines/LIGHT/.venv-light`
- official ParlAI-hosted checkpoint validated:
  - `zoo:dodecadialogue/light_dialog_ft/model`
- runnable protocol added:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_light/protocol/run_light_playable_latency.py`
- 5-item smoke playable-latency batch completed
- 8-item formal playable-latency batch completed
- current summary file:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/baselines/baseline_light/summaries/light_playable_latency_v2_en_summary_2026-04-26.json`
- current role:
  - preferred authoritative external row for the main latency table

## Current table scaffold
- playable-latency scaffold:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- supplementary WorldGeneration row:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`

## Current evidence already usable
- DN first-playable proxy mean: `7.662 s`
- DN first-playable proxy p95: `17.716 s`
- PWR first-playable mean: `0.833 s`
- PWR next-turn mean: `0.837 s`
- WorldGeneration first-playable mean: `0.002 s`
- WorldGeneration next-turn mean: `0.000 s`
- GenAgents first-playable mean: `9.76 s`
- GenAgents next-turn mean: `6.285 s`
- LIGHT first-playable mean: `0.41 s`
- LIGHT next-turn mean: `0.431 s`

## Important interpretation note
- the current main table is now fixed enough for draft writing
- row roles are now:
  - `LIGHT` is the preferred authoritative external row
  - `PWR` is a speed/reference text baseline
  - `GenAgents` is a continuity/state supplement inside the main table
  - `WorldGeneration` is a supplementary world-construction row outside the core main table
- the table is therefore strongest for the claim:
  - DN should be discussed relative to different external generation shapes under the same playable-latency protocol
- it is weaker for the claim:
  - every baseline is a fully faithful DN-like game competitor

## Immediate next execution order
1. treat `main_playable_latency_scaffold_2026-04-26.csv` as the fixed main-table baseline stack
2. use `supplementary_playable_latency_worldgeneration_2026-04-26.csv` when the paper needs a world-construction comparison note
3. next work should focus on paper-facing interpretation or stronger adapter quality, not on re-deciding baseline membership

## Newly added writing bundle
- main interpretation note:
  - `experiments/paper_method_view/0_overview/main_playable_latency_results_interpretation_zh_2026-04-26.md`
- paragraph draft:
  - `experiments/paper_method_view/0_overview/main_playable_latency_results_paragraphs_zh_2026-04-26.md`
- Table 1 caption draft:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/table1_main_playable_latency_caption_zh_2026-04-26.md`
- integrated experiment chapter draft:
  - `experiments/paper_method_view/0_overview/experiment_section_draft_zh_2026-04-26.md`

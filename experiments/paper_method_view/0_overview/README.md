# Paper Method View

This is the paper-writing view organized around the method story rather than raw output sources.

## Current chapter structure

- `1_table1_main_visual_efficiency`: core external-baseline playable-latency table and supplementary WorldGeneration row
- `2_table2_text_planning`: older text-side comparison materials and auxiliary aligned tables
- `3_table3_human_evaluation_optional`: optional human-eval block
- `4_ablations`: module-level analysis for pregeneration, council, and read-wait

## Current source-of-truth writing anchor

For the current paper cycle, the preferred entry bundle is:

- `main_experiment_writing_bundle_index_2026-04-26.md`: source-of-truth index for the frozen main experiment package
- `experiment_section_draft_zh_2026-04-26.md`: Chinese full-section draft aligned to the frozen external-baseline main table
- `main_playable_latency_results_interpretation_zh_2026-04-26.md`: paper-facing interpretation notes for the main playable-latency table
- `figure_table_caption_pack_zh_2026-04-26.md`: caption and in-text reference pack for Table 1, supplementary WorldGeneration, and ablations
- `limitations_zh_2026-04-26.md`: limitations and threats-to-validity for the current main experiment

## Frozen main experiment shape

The current main experiment is intentionally narrowed to one core question:

- under a unified `playable-latency protocol`, how does DN compare with runnable external baselines on the time needed to return playable content?

The frozen core main table is:

- `DN`
- `LIGHT`
- `Plan-Write-Revise`
- `GenAgents`

The frozen supplementary row is:

- `WorldGeneration`

This means the current paper-facing story is:

- main table = external system-shape comparison under a unified playable-latency definition
- supplementary table = WorldGeneration fallback row
- ablations = method explanation for DN's current configuration

## Important reading rule

Do not treat older notes in this folder as automatically current. If there is any conflict:

1. trust `main_experiment_writing_bundle_index_2026-04-26.md`
2. trust `main_playable_latency_scaffold_2026-04-26.csv`
3. trust the latest baseline `status.md` files
4. treat other older notes as archive or drafting support only

Raw original results still remain under `benchmark/`, `efficiency_phase1/`, `efficiency_postfix/`, and `paper_modules/`.

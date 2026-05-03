# Main Experiments Handoff Package

This package reorganizes the current DN main experiment and historical baseline materials into a handoff-friendly entrypoint.

## What this package is for
- hand off the current experiment state to another engineer or agent
- show which results are current ground truth versus historical / smoke / fallback
- provide one place to find main tables, sample reviews, raw artifact indexes, reproduction entrypoints, and status notes

## Recommended reading order
1. `00_overview/README.md`
2. `01_main_tables/TABLE_GUIDE.md`
3. `02_sample_reviews/SAMPLE_GUIDE.md`
4. `05_status_and_history/CURRENT_GROUND_TRUTH.md`
5. `04_repro_entrypoints/REPRO_ENTRYPOINTS.md`

## Current main result focus
- image baseline formal20 first-turn summary: `D:/Projects/DN/remote_baseline_results_20260430/outputs/first_turn_formal20_summary.csv`
- image baseline formal20 next-turn latency summary: `D:/Projects/DN/remote_baseline_results_20260430/outputs/next_turn_formal20_latency_summary.csv`
- formal20 quality review sheets: `D:/Projects/DN/remote_baseline_results_20260430/outputs/formal20_quality_review`
- DN own main playable-latency scaffold: `D:/Projects/DN/experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`

## Non-destructive policy
This handoff package does not rename, move, or overwrite the original experiment result directories. Original source-of-truth paths remain unchanged.

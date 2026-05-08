# Baselines for Main Playable-Latency Experiment

This folder is the single source of truth for DN's external baseline work in the current paper cycle.

## Folder contract

Every baseline folder should keep the same internal structure:

- `README.md`
- `source_links.md`
- `status.md`
- `environment/`
- `protocol/`
- `raw_runs/`
- `summaries/`
- `logs/`

No baseline should enter the paper-facing main table unless its runnable evidence is traceable here through:

- a concrete upstream source
- a baseline-specific protocol script
- raw run artifacts
- summary artifacts
- a status note that explains scope and limitations

## Frozen main-table membership

The core main table is now fixed as:

- `DN`
- `LIGHT`
- `Plan-Write-Revise`
- `GenAgents`

`WorldGeneration` is fixed as a supplementary row and must not re-enter the core main table unless we explicitly reopen the full upstream revival path.

## Current baseline roles

| baseline | current role | current state | table status |
| --- | --- | --- | --- |
| `baseline_light` | authoritative external baseline | runnable, official checkpoint downloaded, 8-item batch complete | in core main table |
| `baseline_plan_write_revise` | speed/reference baseline | runnable, pretrained pack loaded, 5-item batch complete | in core main table |
| `baseline_genagents` | continuity supplement baseline | runnable, 8-item batch complete | in core main table |
| `baseline_worldgeneration` | supplementary fallback baseline | runnable in current cycle through rule-based binary-story fallback path, 8-item batch complete | supplementary only |
| `baseline_storydiffusion` | supplementary visual baseline | blocked on current machine | excluded from current main table |
| `baseline_aidungeon` | legacy open-ended game baseline | no-go in current cycle | excluded from current main table |

## Canonical paper-facing outputs

- core main table source of truth:
  - `../summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- supplementary WorldGeneration row:
  - `../summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`
- shared playable protocol:
  - `../../../baseline_integration/adapters/playable_protocol.py`
- shared subset files:
  - `../../../baseline_integration/subsets/efficiency_playable_subset_v1.json`
  - `../../../baseline_integration/subsets/efficiency_playable_subset_v2.json`
- progress report:
  - `../../../baseline_integration/reports/main_playable_latency_progress_2026-04-26.md`
- execution checklist:
  - `./main_playable_latency_checklist_2026-04-26.md`

## Interpretation rule

The current main experiment is about:

- `first_playable_time_s`
- `next_turn_time_s`
- `success_rate`
- `p95_latency_s`
- `playable_output_completeness`
- `interaction_continuity`

This table is a unified playable-latency comparison across external system shapes. It is not a claim that every external baseline is fully isomorphic to DN.

The role split must stay explicit:

- `LIGHT` = authoritative external row
- `Plan-Write-Revise` = speed/reference row
- `GenAgents` = continuity supplement row
- `WorldGeneration` = supplementary fallback row

The DN row also requires an explicit caveat in paper-facing writing:

- `DN` currently uses fullchain `generate_option` latency as the working `first_playable_time` proxy under the pre-generated setup.

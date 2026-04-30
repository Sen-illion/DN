# Missing Main-Experiment Artifacts

This note is now interpreted under the frozen external-baseline main-table plan.

## Already resolved enough for the current paper cycle

1. A unified baseline comparison table
- resolved for the current main experiment through:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- the current paper-facing main table already freezes:
  - `DN`
  - `LIGHT`
  - `Plan-Write-Revise`
  - `GenAgents`
- `WorldGeneration` is preserved separately in:
  - `experiments/paper_method_view/1_table1_main_visual_efficiency/summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`

5. A baseline raw-run folder
- resolved for the current baseline set at the folder level
- each baseline kept in the paper-facing main experiment should have:
  - upstream source reference
  - runnable protocol
  - raw run artifacts
  - summaries
  - status note

## Still incomplete or only partially resolved

2. A quality comparison table
- still incomplete as a single unified cross-system table
- current quality evidence exists, but is fragmented across:
  - DN native guardrail/effectiveness summaries
  - GenAgents judged outputs
  - protocol-level completeness / continuity signals
- if the paper does not require a separate unified quality table, this can remain future work

3. A polished final submission-facing efficiency table packet
- partially resolved
- the core main table source of truth exists, but there is still room to package:
  - one cleaner final workbook / appendix packet
  - one compact final explanation paragraph tied directly to the frozen CSV
- this is now a packaging task, not a missing experiment-run task

4. A cost/resource table
- still missing
- if the paper does not make cost-efficiency claims, this can be omitted with an explicit note
- if cost becomes important later, add:
  - token cost
  - API request count
  - provider event count
  - model-call count

## Important rule

Do not reopen the current main experiment by expanding into DN parameter matrices or new external baselines unless the paper direction changes. The current missing items are mostly packaging and claim-boundary items, not evidence-blocking items.

# Status

## Current state
- status: environment created, judged scorer added, and 8-item DN-env live run passed
- owner: TBD
- last updated: 2026-04-26
- cloned commit: 96854071

## Goal
What we want from this baseline:
- provide a strong academic baseline for agent-style planning and persistent state evolution
- compare DN against a recognized agent/world simulation system

## Inclusion target
Planned paper role:
- main baseline

Planned target table:
- Table 1 partial support
- Table 2 likely support

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [x] environment created
- [x] baseline runnable
- [x] smoke test passed
- [x] benchmark subset mapped
- [x] raw runs generated
- [x] summary metrics generated
- [x] judge-based scoring generated
- [x] final decision made

## Current blockers
- GenAgents does not naturally emit DN-style options, worldview JSON, or images
- benchmark comparison must stay in the text / agent-state lane unless a stronger adapter is added
- current evidence is strong for text planning/state consistency, but still not directly comparable to DN's full multimodal game loop

## Risks
- protocol mismatch with DN full game loop
- judge-based scores are stronger than heuristics but still not human gold labels
- may need to treat this as a planning/state baseline rather than a full game baseline

## Next action
- designate the 8-item judged run as the current Table 2 source-of-truth candidate
- write the short text-baseline progress report for the paper draft
- decide whether to add a normalized live-run export into `experiments/baseline_integration/normalized_runs/`

## Latest artifact state
- smoke raw run:
  - `raw_runs/genagents_smoke_2026-04-25.json`
- 3-turn pending run:
  - `raw_runs/genagents_consistency_2026-04-25_pending.json`
- consistency summary:
  - `summaries/genagents_consistency_summary_2026-04-25.json`
- per-item sheet:
  - `summaries/genagents_consistency_per_item_2026-04-25.csv`
- Table 2 export row:
  - `../../../../2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-25.csv`
- merged Table 2 scaffold:
  - `../../../../2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-25.csv`
- eval packet:
  - `summaries/genagents_eval_packet_2026-04-25.csv`
  - `summaries/genagents_eval_packet_2026-04-25.md`
- DN-env live run:
  - `raw_runs/genagents_consistency_live_2026-04-26_dn_env.json`
- DN-env live summary:
  - `summaries/genagents_consistency_live_summary_2026-04-26_dn_env.json`
  - `summaries/genagents_consistency_live_per_item_2026-04-26_dn_env.csv`
- DN-env live eval packet:
  - `summaries/genagents_eval_packet_live_2026-04-26_dn_env.csv`
  - `summaries/genagents_eval_packet_live_2026-04-26_dn_env.md`
- DN-env Table 2 row:
  - `../../../../2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-26_dn_env.csv`
- DN-env merged Table 2 scaffold:
  - `../../../../2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env.csv`
- DN-env judged summary:
  - `summaries/genagents_consistency_judged_live_2026-04-26_dn_env.json`
  - `summaries/genagents_consistency_judged_live_2026-04-26_dn_env.csv`
- judge protocol:
  - `protocol/judge_protocol.md`
- expanded subset:
  - `protocol/genagents_consistency_subset_v2.json`
- 8-item live run:
  - `raw_runs/genagents_consistency_live_2026-04-26_dn_env_subset_v2.json`
- 8-item live summary:
  - `summaries/genagents_consistency_live_summary_2026-04-26_dn_env_subset_v2.json`
  - `summaries/genagents_consistency_live_per_item_2026-04-26_dn_env_subset_v2.csv`
- 8-item judged summary:
  - `summaries/genagents_consistency_judged_live_2026-04-26_dn_env_subset_v2.json`
  - `summaries/genagents_consistency_judged_live_2026-04-26_dn_env_subset_v2.csv`
- 8-item eval packet:
  - `summaries/genagents_eval_packet_live_2026-04-26_dn_env_subset_v2.csv`
  - `summaries/genagents_eval_packet_live_2026-04-26_dn_env_subset_v2.md`
- 8-item normalized export:
  - `../../../../../baseline_integration/normalized_runs/genagents_consistency_live_2026-04-26_dn_env_subset_v2.normalized.json`
- 8-item Table 2 row:
  - `../../../../2_table2_text_planning/summary_tables/genagents_table2_row_2026-04-26_dn_env_subset_v2.csv`
- 8-item merged Table 2 scaffold:
  - `../../../../2_table2_text_planning/summary_tables/text_baseline_comparison_merged_2026-04-26_dn_env_subset_v2.csv`

## Final decision
- decision: keep as a main baseline for text planning / state consistency, but not as a full multimodal system baseline
- rationale:
  - local environment and public sample-agent loading are now validated
  - the baseline is authoritative and experimentally relevant to DN's agent-memory claims
  - the baseline now runs successfully against DN's existing `.env` test API configuration
  - the baseline now also has judge-based quality scores for the current live subset
  - the expanded 8-item run reached `turn_success_rate = 0.958`, `item_full_success_rate = 0.875`, and `latency_p95_s = 11.425`
  - it is therefore no longer just integration-ready; it is an actually runnable text-side baseline for the paper

## Playable latency artifacts
- playable latency raw export:
  - `raw_runs/genagents_playable_latency_2026-04-26_subset_v2.json`
- playable latency summary:
  - `summaries/genagents_playable_latency_2026-04-26_subset_v2.csv`
  - `summaries/genagents_playable_latency_summary_2026-04-26_subset_v2.json`
- main playable-latency scaffold row source:
  - `../../summary_tables/main_playable_latency_scaffold_2026-04-26.csv`

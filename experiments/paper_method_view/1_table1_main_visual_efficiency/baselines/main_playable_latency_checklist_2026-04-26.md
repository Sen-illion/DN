# Main Playable-Latency Checklist (2026-04-26)

This checklist is the execution guardrail for the current DN main experiment. Future work should continue from here instead of reopening already-settled scope decisions.

## Locked experiment scope

- [x] main claim fixed to "DN reduces click-to-playable waiting time"
- [x] `end_to_end_boot_time_s` removed from this cycle
- [x] baseline adaptation is allowed if the upstream core mechanism remains visible
- [x] shared playable protocol defined
- [x] shared subset files defined

## Baseline execution order

1. `Plan-Write-Revise`
2. `WorldGeneration`
3. `GenAgents`
4. `StoryDiffusion` only after text-side package is frozen and suitable hardware exists
5. `AIDungeon` deferred unless legacy-runtime branch is explicitly reopened

## Current completion state

- [x] DN row linked into main playable-latency scaffold
- [x] PWR runnable and summarized
- [x] WorldGeneration runnable in current-cycle fallback path and summarized
- [x] GenAgents converted into the same latency protocol and summarized
- [x] LIGHT replacement candidate cloned, environment created, official checkpoint 8-item batch passed
- [ ] decide whether PWR stays as a main-table row or becomes appendix-only speed reference
- [ ] decide whether WorldGeneration current fallback path is sufficient for final submission, or whether a stricter upstream graph-generation revival is still required
- [x] decide that LIGHT is the preferred authoritative main-table row and WorldGeneration moves to supplementary comparison
- [ ] expand one or more main baselines from subset evaluation to a larger formal batch if the paper draft needs stronger statistics
- [ ] write final paper-facing interpretation for why DN is slower/faster on each row and what each row actually means
- [x] write paper-facing interpretation draft for the fixed main table

## Artifact checkpoints

- [x] shared protocol: `../../../baseline_integration/adapters/playable_protocol.py`
- [x] progress report: `../../../baseline_integration/reports/main_playable_latency_progress_2026-04-26.md`
- [x] scaffold table: `../summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- [x] PWR summary: `baseline_plan_write_revise/summaries/pwr_playable_latency_v1_summary_2026-04-26.json`
- [x] WorldGeneration summary: `baseline_worldgeneration/summaries/worldgeneration_playable_latency_v2_summary_2026-04-26.json`
- [x] GenAgents summary: `baseline_genagents/summaries/genagents_playable_latency_summary_2026-04-26_subset_v2.json`
- [x] LIGHT formal summary: `baseline_light/summaries/light_playable_latency_v2_en_summary_2026-04-26.json`
- [x] WorldGeneration supplementary row: `../summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`
- [x] Table 1 caption draft: `../summary_tables/table1_main_playable_latency_caption_zh_2026-04-26.md`
- [x] main results interpretation draft: `../../0_overview/main_playable_latency_results_interpretation_zh_2026-04-26.md`
- [x] main results paragraphs draft: `../../0_overview/main_playable_latency_results_paragraphs_zh_2026-04-26.md`
- [x] experiment section draft integrated with fixed playable-latency main table: `../../0_overview/experiment_section_draft_zh_2026-04-26.md`

## Next priority decisions

- [ ] assess semantic validity vs latency validity for PWR
- [ ] assess whether WorldGeneration should be reported as "rule-based playable reconstruction" or "interactive fiction world-construction fallback"
- [x] assess that LIGHT should be preferred over WorldGeneration for main-table authority, despite limited semantic fit
- [ ] choose whether the next engineering effort goes into:
  - stronger adapter quality for existing baselines
  - larger sample runs
  - a new authoritative runnable baseline

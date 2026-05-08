# Run Protocol

## Intended comparison scope
- DN planning / state-consistency comparison

## Planned benchmark mapping
- task source: benchmark subset adapted for stateful progression
- smoke subset: `genagents_smoke_subset_v1.json`
- smoke subset size: 3
- consistency subset: `genagents_consistency_subset_v1.json`
- consistency subset size: 3 x 3 turns
- mode: agent-world / text-planning

## Current mapped task shape
For each benchmark item:
- convert `theme` into an interview-style scenario stimulus
- preserve `expected_genre` and `expected_tone` as response framing hints
- use `must_have_constraints` and `forbidden_issues` as evaluation rubric fields
- ask the baseline for a persona-consistent response rather than DN-style branching options

## Normalized outputs required
- benchmark id
- agent profile
- prompt bundle
- turn outputs
- success / failure status
- latency

## Smoke test result
- public sample-agent loading works locally
- benchmark subset mapping is defined
- active LLM generation is pending only on `OPENAI_API_KEY`

## Ready-to-run scripts
- smoke loader:
  - `protocol/run_genagents_smoke.py`
- 3-turn consistency runner:
  - `protocol/run_genagents_consistency.py`
- run summarizer:
  - `protocol/summarize_genagents_runs.py`
- Table 2 row exporter:
  - `protocol/export_genagents_table2_row.py`
- Table 2 scaffold merger:
  - `protocol/merge_genagents_into_table2_scaffold.py`
- eval packet builder:
  - `protocol/build_genagents_eval_packet.py`

## Notes
- If the full DN game-loop mapping is too forced, keep this baseline in a clearly delimited subtask protocol.

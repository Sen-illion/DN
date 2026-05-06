# Status

## Current state
- status: playable-latency fallback path is runnable and 8-item batch has completed
- last updated: 2026-04-26
- cloned commit: 5e97df013399e1a401d0a7ec184c4b9eb3100edd

## Frozen paper role
- `WorldGeneration` is retained as a supplementary fallback row only
- it must not be described as a core main-table winner/loser baseline in the current paper cycle

## Goal
- preserve a world-construction-oriented comparison row for supplementary material
- document a paper-backed world-generation direction without overstating current runnable fidelity

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [x] baseline folder scaffolded
- [x] playable conversion helper added
- [x] current-cycle runnable protocol added
- [x] 5-item playable latency run generated
- [x] 8-item playable latency run generated
- [x] summary metrics generated
- [ ] stricter upstream graph-generation revival validated on DN benchmark items

## What actually ran
- the current runnable path uses the official `rule-based/binary_data/*_binary.txt` assets from WorldGeneration
- a local fallback protocol reconstructs a playable room graph from those upstream binary story triples
- the fallback replaces unavailable legacy dependencies:
  - `neuralcoref`
  - old `spacy.load('en')`
  - Stanford NER jar/classifier wiring
- this keeps the evaluation anchored to upstream story-extraction assets while making the pipeline reproducible on the current machine

## Current limitations
- this is not yet a full faithful revival of the original paper pipeline from DN benchmark prompt -> OpenIE/coref/NER -> graph -> Evennia world
- latency numbers therefore reflect:
  - rule-based binary-story reconstruction
  - graph assembly
  - playable adapter rendering
- latency numbers do not yet include the unavailable legacy NLP preprocessing stack

## Current interpretation
- latency-valid: yes
- task-shape-valid: medium
- semantic alignment with DN benchmark themes: limited
- final paper role at this moment:
  - supplementary fallback world-construction row
  - not part of the core main-table conclusion set

## Latest artifact state
- 5-item raw run:
  - `raw_runs/worldgeneration_playable_latency_v1_2026-04-26.json`
- 5-item summary:
  - `summaries/worldgeneration_playable_latency_v1_2026-04-26.csv`
  - `summaries/worldgeneration_playable_latency_v1_summary_2026-04-26.json`
- 8-item raw run:
  - `raw_runs/worldgeneration_playable_latency_v2_2026-04-26.json`
- 8-item summary:
  - `summaries/worldgeneration_playable_latency_v2_2026-04-26.csv`
  - `summaries/worldgeneration_playable_latency_v2_summary_2026-04-26.json`
- runnable protocol:
  - `protocol/run_worldgeneration_playable_latency.py`

## Final paper packaging rule
- keep this row only in the supplementary comparison file
- explicitly note that the current runnable path is a fallback reconstruction path rather than the full original pipeline
- only reopen core-table discussion if a stricter upstream-faithful revival is actually completed

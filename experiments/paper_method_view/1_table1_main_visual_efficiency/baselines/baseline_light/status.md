# Status

## Current state
- status: repo cloned, environment created, official ParlAI-hosted LIGHT-related checkpoint downloaded, 5-item and 8-item playable-latency batches completed
- last updated: 2026-04-26
- cloned commit: 71a06cae8573048b1af41507ac52fe33b650fab3

## Frozen paper role
- `LIGHT` is the preferred authoritative external baseline in the core main playable-latency table
- it should be interpreted as an external interaction/dialogue reference row, not as a fully isomorphic DN replacement system

## Goal
- provide the strongest paper-facing external baseline row for the unified playable-latency comparison
- compare DN against a research-backed interactive fantasy dialogue / game-world system with stronger upstream authority than the current WorldGeneration fallback path

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [x] baseline folder scaffolded
- [x] environment created
- [x] checkpoint download validated
- [x] one-turn smoke inference passed
- [x] 5-item playable latency batch generated
- [x] 8-item playable latency batch generated
- [x] summary metrics generated

## What actually ran
- repo source: official `facebookresearch/LIGHT`
- runtime model path: official ParlAI-hosted checkpoint
  - `zoo:dodecadialogue/light_dialog_ft/model`
- current benchmark protocol:
  - shared DN playable-latency schema
  - English prompt adapter added to reduce mismatch with the released LIGHT checkpoint

## Current results
- 5-item English-adapter summary:
  - `summaries/light_playable_latency_v1_en_summary_2026-04-26.json`
- 8-item English-adapter summary:
  - `summaries/light_playable_latency_v2_en_summary_2026-04-26.json`
- current 8-item metrics:
  - `first_playable_time_mean_s = 0.41`
  - `p95_latency_s = 0.477`
  - `next_turn_time_mean_s = 0.431`
  - `success_rate = 1.0`

## Current interpretation
- authority: strong
- interaction shape vs DN: medium-to-strong
- latency evidence: strong
- semantic fit on DN's Chinese benchmark themes: still limited

## Important limitation
- the current released runnable checkpoint tends to collapse toward short refusal-like or generic dialogue replies under this protocol
- therefore `LIGHT` is currently much stronger as:
  - an authoritative external latency/reference row
- than as:
  - a semantically faithful DN-like content baseline

## Latest artifact state
- runnable protocol:
  - `protocol/run_light_playable_latency.py`
- 5-item raw run:
  - `raw_runs/light_playable_latency_v1_en_2026-04-26.json`
- 5-item summary:
  - `summaries/light_playable_latency_v1_en_2026-04-26.csv`
  - `summaries/light_playable_latency_v1_en_summary_2026-04-26.json`
- 8-item raw run:
  - `raw_runs/light_playable_latency_v2_en_2026-04-26.json`
- 8-item summary:
  - `summaries/light_playable_latency_v2_en_2026-04-26.csv`
  - `summaries/light_playable_latency_v2_en_summary_2026-04-26.json`

## Final paper packaging rule
- keep `LIGHT` in the core main table
- describe it as the preferred authoritative external row under the unified playable-latency protocol
- do not describe it as a fully equivalent DN-like multimodal game system

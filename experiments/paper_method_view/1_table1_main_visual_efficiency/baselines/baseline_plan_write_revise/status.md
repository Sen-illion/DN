# Status

## Current state
- status: environment revived, official model pack downloaded, and 5-item playable latency run passed
- last updated: 2026-04-26
- cloned commit: b394657b1bd1d6978ea31d6ac5bad6f3a4b6e1da

## Goal
- provide a main baseline for on-demand story continuation latency
- compare DN's pre-generation against a specialized narrative model under the same playable-response definition

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [x] baseline folder scaffolded
- [x] playable protocol mapped
- [x] runnable adapter script added
- [x] environment created
- [x] pretrained models downloaded
- [x] smoke test passed
- [x] 5-item latency batch generated
- [x] summary metrics generated

## Current blockers
- upstream model quality is weak on DN-style Chinese benchmark prompts and behaves like a lightweight English ROCStories model
- the current comparison is latency-valid but not yet quality-aligned with DN game semantics

## Next action
- decide whether to keep PWR as a pure speed/reference baseline or constrain it further with a stronger premise-to-playable adapter
- if kept for the main table, pair its latency row with a limitation note that it is a text-only on-demand narrative baseline

## Latest artifact state
- smoke1 raw run:
  - `raw_runs/pwr_playable_latency_smoke1_2026-04-26.json`
- smoke1 summary:
  - `summaries/pwr_playable_latency_smoke1_2026-04-26.csv`
  - `summaries/pwr_playable_latency_smoke1_summary_2026-04-26.json`
- 5-item playable latency run:
  - `raw_runs/pwr_playable_latency_v1_2026-04-26.json`
- 5-item playable latency summary:
  - `summaries/pwr_playable_latency_v1_2026-04-26.csv`
  - `summaries/pwr_playable_latency_v1_summary_2026-04-26.json`
- server logs:
  - `logs/pwr_server_stdout_2026-04-26.log`
  - `logs/pwr_server_stderr_2026-04-26.log`

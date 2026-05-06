# Baseline: AIDungeon

## Role in paper
This baseline is included as a main baseline for open-ended AI interactive narrative.

Planned role:
- main baseline

Target comparison dimensions:
- interactive narrative
- multi-turn story continuation
- playability
- response efficiency

## Why this baseline
Why this project is representative and worth comparing:
- AIDungeon is one of the most recognizable open-ended AI narrative game systems.
- It is highly aligned with the core task form of DN: user-driven story progression.
- It provides a strong task-shape comparison even if its engineering stack is older.

## What part of DN it is meant to compare
Closest DN capability:
- player-driven dynamic story continuation
- multi-turn interactive narrative generation

Not intended to cover:
- DN-style pregeneration
- DN-style multimodal image generation pipeline
- DN-style structured worldview caching

## Planned experimental mode
Planned mode for this baseline:
- text-first main experiment
- optional visual comparison only if a stable image pipeline exists

Expected benchmark mapping:
- input source: benchmark subset derived from `DN-quality-benchmark-v1`
- output normalization target: unified main-experiment schema
- sample size target: TBD after smoke test

## Current decision
Status:
- planned

Main risk:
- repo is older and may be difficult to run cleanly in current environments

Decision note:
- if runnable, this should remain a main baseline because the task form matches DN well

## Output structure
Expected files in this folder:
- `source_links.md`
- `status.md`
- `environment/`
- `protocol/`
- `raw_runs/`
- `summaries/`
- `logs/`

## Notes
- Use this baseline mainly for task-form comparison, not as a full multimodal engineering comparison.

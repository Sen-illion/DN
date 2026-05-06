# Baseline: StoryDiffusion

## Role in paper
This baseline is included as a supplementary baseline and a strong multimodal comparison target.

Planned role:
- supplementary baseline
- possible visual-subexperiment main baseline

Target comparison dimensions:
- visual consistency
- character consistency across scenes
- text-image alignment
- multimodal story presentation

## Why this baseline
Why this project is representative and worth comparing:
- It is a high-visibility recent research project for story visualization.
- It is directly relevant to DN’s multimodal claim.
- It provides a stronger visual-story comparison than older text-only systems.

## What part of DN it is meant to compare
Closest DN capability:
- scene image generation
- multi-scene visual consistency
- story-to-image alignment

Not intended to cover:
- DN-style open interactive branching gameplay
- DN-style pregeneration / read-wait architecture
- DN-style full end-to-end game server workflow

## Planned experimental mode
Planned mode for this baseline:
- multimodal-subtask comparison

Expected benchmark mapping:
- input source: multimodal subset derived from `DN-quality-benchmark-v1`
- output normalization target: unified main-experiment schema
- sample size target: TBD after smoke test

## Current decision
Status:
- documented and environment-checked; blocked for execution on the current machine

Main risk:
- not a full interactive story game system, so it should not be oversold as a full-system baseline

Decision note:
- highly valuable for visual and multimodal evidence even if not used as the single main system baseline
- on the current Windows machine, this baseline should be treated as prepared-but-blocked until a CUDA-capable runtime is available

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
- Use this baseline to strengthen DN’s multimodal comparison, not to replace task-form baselines such as AIDungeon.

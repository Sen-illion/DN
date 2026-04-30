# Baseline: genagents

## Role in paper
This baseline is included as a main baseline for agent-driven world and character simulation.

Planned role:
- main baseline

Target comparison dimensions:
- character consistency
- world-state stability
- long-range behavior coherence
- agent-style planning dynamics

## Why this baseline
Why this project is representative and worth comparing:
- It comes from a high-authority academic source and is directly tied to influential generative-agent work.
- It represents the agent/world-simulation side of interactive narrative systems.
- It helps position DN as more than a prompt-based branching story generator.

## What part of DN it is meant to compare
Closest DN capability:
- persistent state evolution
- character/world consistency across multiple steps

Not intended to cover:
- DN-style full player-choice game loop
- DN-style scene-image generation pipeline
- DN-style production-oriented web system flow

## Planned experimental mode
Planned mode for this baseline:
- agent-world subtask comparison
- text-planning / long-range consistency comparison

Expected benchmark mapping:
- input source: benchmark subset adapted for stateful text progression
- output normalization target: unified main-experiment schema
- sample size target: TBD after smoke test

## Current decision
Status:
- planned

Main risk:
- mapping DN benchmark tasks to agent-simulation protocol may require task adaptation

Decision note:
- this is still worth keeping because of authority and conceptual relevance

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
- If full system comparison is too forced, use this baseline for the planning/state-consistency block and document that clearly.

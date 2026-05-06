# DN Baseline Integration Layer

This folder is the adapter layer between external baselines and the DN benchmark harness.

## Goal
Make every baseline export comparable artifacts without forcing every upstream project into the DN server shape.

## Design
- `schema/`: unified baseline output schema and playable-latency schema
- `adapters/`: per-baseline mapping logic and conversion scripts
- `subsets/`: benchmark subsets adapted for each baseline family
- `reports/`: integration status and coverage reports
- `normalized_runs/`: baseline outputs normalized for DN comparison tables

## Current main-experiment focus
This cycle targets the playable-latency claim:
- `first_playable_time_s`
- `next_turn_time_s`
- `success_rate`
- `p95_latency_s`
- `playable_output_completeness`
- `interaction_continuity`

## Principle
DN should compare baselines under one evaluation protocol, but not every baseline needs to share one runtime architecture.

The integration layer therefore normalizes:
- input task selection
- prompt / scenario mapping
- output fields
- success and failure logging
- downstream metric computation
- playable-response timing semantics

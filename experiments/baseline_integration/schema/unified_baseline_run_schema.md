# Unified Baseline Run Schema

Every baseline run exported into DN comparison tables should ideally contain these fields:

## Required fields
- `baseline_id`
- `benchmark_id`
- `run_id`
- `mode`
- `input_bundle`
- `raw_output`
- `success`
- `latency_s`

## Recommended fields
- `agent_profile`
- `world_state`
- `options`
- `image_artifacts`
- `failure_reason`
- `resource_usage`
- `notes`

## Why
This schema lets DN compare:
- full-system baselines
- text-only baselines
- multimodal baselines

without pretending they all expose the same upstream API.

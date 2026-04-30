# Playable Latency Run Schema

This schema extends the unified baseline run format for DN's main latency experiment.

## Purpose
Measure how long an external baseline needs to return a playable game response after a player click.

## Required top-level fields
- `baseline_id`
- `benchmark_id`
- `run_id`
- `mode`: `first_playable` or `next_turn`
- `input_bundle`
- `raw_output`
- `success`
- `latency_s`
- `playable`
- `playable_components`
- `normalized_response`

## Required normalized response fields
- `scene_setup`
- `player_state`
- `narrative_response`
- `candidate_actions` or `suggested_next_step`
- `is_playable`
- `request_start_ts`
- `first_playable_ts`
- `finish_ts`
- `error`

## Playable definition
A response counts as playable when at least 3 of the following hold:
- the player can infer the current scene / situation
- the player can infer who they are or what state they are in
- the system gives concrete next actions or a direct next step
- the next turn can be continued using the returned state

## Main derived metrics
- `first_playable_time_s`
- `next_turn_time_s`
- `success_rate`
- `p95_latency_s`
- `playable_output_completeness`
- `interaction_continuity`

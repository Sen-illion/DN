# Plan-Write-Revise Baseline

This baseline adapts the official Plan-Write-Revise story generation system into DN's playable latency protocol.

## Intended paper role
- main external baseline for on-demand plot generation
- used to compare DN against a specialized story generation system rather than a generic chat model

## Runtime shape
- upstream repo: `experiments/external_baselines/plan_write_revise`
- upstream API path: `server/web_server.py`
- DN adapter path: `protocol/run_pwr_playable_latency.py`

## What counts as a playable output here
The adapter keeps PWR's storyline + story generation core, then wraps the output into:
- a scene setup
- a player-state summary
- 2-4 candidate actions
- a next-turn continuation target

This means the baseline is adapted for playable comparison, but the narrative text still comes from the upstream PWR system.

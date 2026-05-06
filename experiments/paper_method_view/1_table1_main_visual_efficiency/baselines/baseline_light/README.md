# LIGHT Baseline

This baseline targets the official Meta `LIGHT` ecosystem and uses the released ParlAI-hosted `dodecadialogue/light_dialog_ft` checkpoint as the first runnable entry point.

## Why this baseline exists

Compared with the current `WorldGeneration` fallback path, LIGHT is:

- more clearly a game-like interactive narrative system
- backed by an influential research project rather than a lightly maintained legacy pipeline
- closer to DN in "character/world/player utterance" interaction shape

## Scope in the current cycle

The current runnable slice is:

- official LIGHT-related pretrained dialogue model
- wrapped into DN's playable-latency protocol
- text-side only

This is not yet the full multiplayer LIGHT game server or full world simulator benchmark.

## Upstream anchors

- repo clone:
  - `C:\Users\zhang\Desktop\DN\experiments\external_baselines\LIGHT`
- runnable local environment:
  - `C:\Users\zhang\Desktop\DN\experiments\external_baselines\LIGHT\.venv-light`
- protocol runner:
  - `protocol/run_light_playable_latency.py`

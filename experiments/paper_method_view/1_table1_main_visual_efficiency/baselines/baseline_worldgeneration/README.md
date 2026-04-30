# WorldGeneration Baseline

This baseline adapts the official WorldGeneration project into DN's playable latency protocol.

## Intended paper role
- main external baseline for world / scenario construction
- compares DN against a paper-backed interactive fiction world generator

## Runtime shape
- upstream repo: `experiments/external_baselines/worldgeneration`
- current DN adapter path: `protocol/convert_worldgeneration_graph_to_playable.py`

## Scope in the current cycle
The first implementation stage targets graph-to-playable conversion. The upstream neural / rule-based world creation path still needs a dedicated environment before full benchmark runs are possible.

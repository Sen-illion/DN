# GenAgents Adapter

## Baseline nature
- text-only
- agent-memory driven
- OpenAI API dependent

## Adapter strategy
- use DN benchmark themes as interview stimuli
- preserve benchmark ids
- convert each item into a short multi-turn dialogue task
- export normalized turn outputs and latency

## Minimal adapter responsibilities
- load one public sample agent
- attach scenario prompt generated from benchmark item
- run 1-turn smoke test first
- later extend to 3-turn consistency test

## Evaluation fit
- strong: coherence, consistency, usefulness
- weak: image and full interactive game metrics

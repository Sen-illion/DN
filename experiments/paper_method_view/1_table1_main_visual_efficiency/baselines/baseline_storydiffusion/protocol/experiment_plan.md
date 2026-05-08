# StoryDiffusion Experiment Plan

## Why this baseline is being run now
DN already has internal evidence for:
- complete-system efficiency
- guardrail / reliability proxies
- text planning support
- module ablations

The missing paper-ready evidence is external baseline comparison. StoryDiffusion is the first baseline to run because it is the cleanest fit for the visual and multimodal part of Table 1.

## Confirmed comparison scope
StoryDiffusion will be used for:
- visual consistency comparison
- character consistency across scenes
- text-image alignment
- image usable rate

StoryDiffusion will not be used as a full interactive branching-game baseline unless that capability is explicitly implemented and validated.

## Planned execution stages
### Stage 1: Environment smoke test
Goal:
- verify that the upstream code can launch locally with a dedicated environment
- verify whether SDXL-scale dependencies can run on the current machine

Exit criteria:
- dependency installation succeeds
- app import path is stable
- one minimal generation call or equivalent startup path succeeds

### Stage 2: Benchmark smoke subset
Subset file:
- `storydiffusion_smoke_subset_v1.json`

Goal:
- run 2 representative samples
- confirm generation latency, artifact layout, and failure logging conventions

Exit criteria:
- at least 1 successful generated artifact bundle
- latency and failure reasons are recorded in a normalized way

### Stage 3: Main visual subset
Subset file:
- `storydiffusion_visual_subset_v1.json`

Goal:
- produce one representative sample per style family
- feed outputs into DN visual evaluation and summary pipeline

Exit criteria:
- raw runs written to `raw_runs/`
- generated images written to `artifacts/`
- summary metrics written to `summaries/`

## Expected downstream use
If Stage 1 and Stage 2 succeed, StoryDiffusion should be used in:
- Table 1 visual block
- visual-quality supporting evidence

If Stage 1 fails because of hardware/runtime mismatch, keep the baseline documented but mark it as blocked or dropped with reasons in `status.md`.

# Status

## Current state
- status: environment created, smoke test blocked on current machine
- owner: TBD
- last updated: 2026-04-26
- cloned commit: 8de45e4

## Goal
What we want from this baseline:
- provide a strong multimodal comparison target
- compare DN on visual consistency and text-image alignment

## Inclusion target
Planned paper role:
- supplementary baseline
- visual-subexperiment baseline

Planned target table:
- Table 1 visual block
- visual-quality supporting evidence

## Reproduction progress
- [x] source confirmed
- [x] repo cloned
- [x] environment created
- [~] baseline runnable
- [ ] smoke test passed
- [x] benchmark subset mapped
- [ ] raw runs generated
- [ ] summary metrics generated
- [x] final decision made

## Current blockers
- current environment is CPU-only: `torch 2.0.1+cpu`, `torch.cuda.is_available() == False`
- upstream low-VRAM entry still tries to load an SDXL-scale pipeline and PhotoMaker assets, which is not practical on this machine for a paper-grade batch run
- Windows startup required extra compatibility fixes before the app could even enter model download:
  - set `PYTHONUTF8=1` to avoid `gradio` import failure under `gbk`
  - upgrade `huggingface-hub` from `0.20.2` to `0.24.6` to match `accelerate 0.32.1`

## Risks
- protocol mismatch with full interactive narrative system
- likely suitable only for multimodal subtask comparison
- StoryDiffusion loads SDXL-scale components and PhotoMaker assets, so startup and inference cost are high even before benchmark execution
- `xformers` CUDA extensions are unavailable in the current environment

## Next action
- do not spend more execution time forcing StoryDiffusion during the current paper cycle
- keep it as a documented supplementary baseline that requires a CUDA-capable box for actual benchmark runs
- only reopen this branch when a CUDA-capable machine is available and the text-side baseline package is already frozen

## Final decision
- decision: blocked on current machine, keep as supplementary baseline only
- rationale:
  - startup now reaches the upstream model-download stage, so the repo and environment wiring are basically understood
  - however, the current box exposes no CUDA device, while upstream explicitly targets SDXL-scale generation and recommends >20 GB GPU memory
  - this makes StoryDiffusion unsuitable as the next main baseline to run for the DN paper on the present hardware
  - therefore it should remain a deferred visual-subexperiment branch rather than an active execution target

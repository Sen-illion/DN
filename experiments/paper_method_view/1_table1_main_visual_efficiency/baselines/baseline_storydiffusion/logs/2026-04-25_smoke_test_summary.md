# StoryDiffusion Smoke Test Summary

## Scope
- baseline: `baseline_storydiffusion`
- date: 2026-04-25
- machine: current DN Windows workspace machine
- goal: verify whether the upstream local demo can become benchmark-runnable

## Commands used
- basic runtime check:
  - `python -c "import torch, diffusers, gradio; ..."`
- startup smoke test:
  - `python gradio_app_sdxl_specific_id_low_vram.py`

## What was confirmed
- dedicated Python 3.10 environment works
- `torch`, `diffusers`, and `gradio` can import when `PYTHONUTF8=1` is set
- the upstream script reaches model bootstrap logic
- `data/photomaker-v1.bin` was downloaded successfully
- the SDXL model repository started fetching from Hugging Face

## Problems found
- the first environment build had a dependency mismatch:
  - `accelerate 0.32.1` expected a newer `huggingface-hub` than `0.20.2`
- after fixing that, the bigger blocker remained:
  - runtime is CPU-only
  - `xformers` CUDA extensions are unavailable
  - upstream README recommends a >20 GB GPU setup even for the low-VRAM path

## Operational conclusion
- StoryDiffusion is integrated enough to document as a supplementary visual baseline
- StoryDiffusion is not the right next runnable main baseline on this machine
- use a CUDA-capable machine if DN later needs actual StoryDiffusion benchmark numbers

## Recommended project action
1. keep StoryDiffusion in the paper as a visual-subexperiment candidate only
2. move active baseline execution to `baseline_genagents`
3. use `baseline_aidungeon` as the other main comparative branch for interactive narrative behavior

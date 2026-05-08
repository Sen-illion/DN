# Environment Setup

## Goal
Record the exact installation and runtime setup for this baseline.

## Machine
- OS: Windows (current DN workspace machine)
- Python: current system Python is 3.13.9
- dedicated baseline Python: 3.10.11 (`.venv-storydiffusion`)
- CUDA: not available in the active StoryDiffusion environment
- GPU: `nvidia-smi` not found in current shell PATH
- torch runtime: `torch 2.0.1+cpu`

## Observed runtime requirements from upstream repo
- Python >= 3.8
- PyTorch 2.0.1
- torchvision 0.15.2
- diffusers 0.25.0
- gradio 4.22.0
- xformers 0.0.20
- SDXL-based pipeline plus PhotoMaker weights downloaded via Hugging Face

## Important codepath notes
- `app.py` imports `hf_hub_download(...)` at import time for `TencentARC/PhotoMaker`
- `app.py` builds SDXL pipelines from pretrained Hugging Face models
- upstream README recommends a >20 GB GPU setup for the provided demo path

## Steps
1. Created a dedicated Python 3.10 environment:
   - `py -3.10 -m venv .venv-storydiffusion`
2. Installed upstream-style dependencies in that environment:
   - `torch==2.0.1`
   - `torchvision==0.15.2`
   - `gradio==4.22.0`
   - `diffusers==0.25.0`
   - `transformers==4.36.2`
   - `huggingface-hub==0.20.2` initially, later upgraded to `0.24.6`
   - `xformers==0.0.20`
   - `spaces==0.19.4`
   - `accelerate==0.32.1`
   - `safetensors==0.4.0`
   - `omegaconf`
   - `peft`
   - `httpx==0.27.0`
3. Validated runtime basics:
   - `torch.cuda.is_available() == False`
   - `torch.cuda.device_count() == 0`
4. Fixed two startup blockers:
   - set `PYTHONUTF8=1` before launching Python to avoid a Windows `gradio` import `UnicodeDecodeError`
   - upgraded `huggingface-hub` to `0.24.6` because `accelerate 0.32.1` could not import from `0.20.2`
5. Ran a startup smoke test with:
   - `python gradio_app_sdxl_specific_id_low_vram.py`
   - result: app entered model-download stage and fetched `photomaker-v1.bin`, but no benchmark-ready generation was reached on this machine

## Runtime assets
- checkpoint / model: `stablediffusionapi/sdxl-unstable-diffusers-y` plus PhotoMaker assets
- inference mode: local
- downloaded asset confirmed:
  - `data/photomaker-v1.bin`

## Notes
- startup evidence is saved under:
  - `logs/2026-04-25_startup_stdout.log`
  - `logs/2026-04-25_startup_stderr.log`
- stderr shows `xformers` CUDA extensions are unavailable because the environment is CPU-only
- the current machine is sufficient to document integration requirements, but not sufficient for a convincing StoryDiffusion benchmark run

# DN Baseline Runners

This folder contains newly cloned external baselines plus lightweight DN-side
runners. The runners do not modify upstream repositories; they adapt DN-style
benchmark items into prompts and write comparable JSON/image artifacts.

## Subsets

- `baselines/subsets/dn_style_smoke3.json`: quick remote validation subset.
- `baselines/subsets/dn_style_formal8.json`: first formal image-baseline subset.

Regenerate them from the DN benchmark:

```bash
python scripts/baselines/export_dn_style_subsets.py
```

## Remote cache convention

Use the AutoDL data disk:

```bash
export HF_HOME=/root/autodl-tmp/hf_cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf_cache
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache
export HF_ENDPOINT=https://hf-mirror.com
```

The first remote StoryDiffusion attempt failed because `huggingface.co` was not
reachable from the machine. Use the mirror endpoint above unless direct HF
access is confirmed.

## Remote control scripts

After unpacking the lite package on the AutoDL machine:

```bash
cd /root/autodl-tmp/DN
bash scripts/baselines/remote_autodl_setup.sh
bash scripts/baselines/remote_status_check.sh
```

Set up SDM-v2 separately after StoryDiffusion smoke succeeds:

```bash
bash scripts/baselines/remote_sdmv2_setup.sh
```

Run batches through the wrapper:

```bash
bash scripts/baselines/remote_run_image_baselines.sh story-smoke
bash scripts/baselines/remote_run_image_baselines.sh story-formal
bash scripts/baselines/remote_run_image_baselines.sh sdm-smoke
bash scripts/baselines/remote_run_image_baselines.sh sdm-formal
```

## StoryDiffusion

Preferred first GPU baseline on the 4090 machine:

```bash
python scripts/baselines/run_storydiffusion.py \
  --subset baselines/subsets/dn_style_smoke3.json \
  --output /root/autodl-tmp/outputs/storydiffusion_smoke3
```

The runner loads `baselines/StoryDiffusion/gradio_app_sdxl_specific_id_low_vram.py`
without launching Gradio and calls its `process_generation` function.

For DN batch mode the runner skips the upstream script's eager PhotoMaker
download because the textual-description path does not use PhotoMaker. This
prevents an unused model download from blocking the smoke run.

## SDM-v2

The requested GitHub repository URL was not cloneable, so the runnable path uses
Hugging Face Diffusers and model id `stabilityai/stable-diffusion-2-1-base`:

```bash
python scripts/baselines/run_sdmv2.py \
  --subset baselines/subsets/dn_style_smoke3.json \
  --output /root/autodl-tmp/outputs/sdmv2_smoke3
```

This is a single-image baseline and does not claim character consistency.

## IC-LoRA

The first runner records structured blocked artifacts until ComfyUI and IC-LoRA
weights are configured:

```bash
python scripts/baselines/run_iclora.py \
  --subset baselines/subsets/dn_style_smoke3.json \
  --output /root/autodl-tmp/outputs/iclora_smoke3
```

Do not train IC-LoRA in the first pass.

## Summaries

Aggregate completed runs:

```bash
python scripts/baselines/summarize_image_baselines.py \
  /root/autodl-tmp/outputs/storydiffusion_smoke3/<run_id> \
  /root/autodl-tmp/outputs/sdmv2_smoke3/<run_id> \
  --output /root/autodl-tmp/outputs/image_baseline_summary.csv
```

Download lightweight results back to Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/baselines/download_autodl_baseline_results.ps1
```

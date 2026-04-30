# Baseline Reproduction Wrappers

This setup standardizes baseline inputs/outputs for local generation experiments.

## Environment Check

- Repository root: `C:\Users\User\Desktop\DN-main`
- Python shim: not configured through `pyenv` (`python` asks for a pyenv version)
- Usable local Python: `C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe`
- `.venv` Python: `3.12.13`
- `.venv` torch: `2.11.0+cpu`
- CUDA: unavailable from torch
- `nvidia-smi`: not found
- `OPENAI_API_KEY`: not set
- `HF_TOKEN` / `HUGGINGFACE_HUB_TOKEN`: not set

## Unified Data

- Input sample: `data/input_samples.jsonl`
- Text outputs: `outputs/text/`
- Image outputs: `outputs/image/`

Input JSONL schema:

```json
{"id":"sample_001","prompt":"...","characters":["..."],"scene":"...","story_context":""}
```

## Baseline Status

| Baseline | Type | Source URL | Official | Local path | Current status | Smoke test |
| --- | --- | --- | --- | --- | --- | --- |
| DOC | Text | https://github.com/facebookresearch/doc-storygen-v2 | Official, but skipped here | `baselines/text/doc-storygen-v2` | User confirmed existing local DOC experiments are complete; not re-run | Skipped by request |
| Rolling | Text | DOC rolling baseline script / CCI description | Not independent official repo | `baselines/text/rolling` | Not implemented per user instruction | Skipped |
| w/oIG | Text | CCI ablation description | Not independent official repo | `baselines/text/wo_ig` | Not implemented per user instruction | Skipped |
| w/oMW | Text | CCI ablation description | Not independent official repo | `baselines/text/wo_mw` | Not implemented per user instruction | Skipped |
| SDM-v2 | Image | https://huggingface.co/stabilityai/stable-diffusion-2-1-base | Official model via Diffusers wrapper | `baselines/image/sdm_v2` | Wrapper supports full JSONL batch generation and low-VRAM flags; local `.venv` lacks `diffusers`; SSH GPU env has dependencies installed but model download needs authorized HF access/cache | Blocked: no generated image; Hugging Face returned auth/cache error |
| StoryDiffusion | Image | https://github.com/HVision-NKU/StoryDiffusion | Official code | `baselines/image/StoryDiffusion` | Official code copied from existing local repo; manifest wrapper implemented | Passed prepare-only manifest |
| IC-LoRA | Image | https://github.com/ali-vilab/In-Context-LoRA | Official repo/workflow | `baselines/image/In-Context-LoRA` | Official workflow copied from existing local repo; ComfyUI workflow preparation implemented | Passed prepare-only manifest |

## Installation

### SDM-v2

```bash
pip install -r baselines/image/sdm_v2/requirements.txt
```

If the model requires Hugging Face authorization:

```bash
set HF_TOKEN=your_huggingface_token
```

PowerShell:

```powershell
$env:HF_TOKEN="your_huggingface_token"
```

On the SSH GPU machine used for this run, the working environment is:

```bash
ssh -p 14077 root@connect.cqa1.seetacloud.com
mkdir -p /root/autodl-tmp/baselines
cd /root/autodl-tmp/baselines
/root/miniconda3/envs/dn/bin/python -m venv --system-site-packages sdm_v2_venv
sdm_v2_venv/bin/python -m pip install diffusers transformers accelerate safetensors
```

The venv reuses the existing CUDA torch from `/root/miniconda3/envs/dn` (`torch 2.6.0+cu124`) to avoid reinstalling multi-GB CUDA wheels. The model itself is not vendored in this repository. If it is not already cached, expect roughly 5-6 GB of Hugging Face downloads for `stabilityai/stable-diffusion-2-1-base`. If Hugging Face gates the repository, log in with a token that has accepted the model license/agreement.

Low-resource options:

- Use `--dtype float16` only on CUDA.
- Use `--attention_slicing`.
- Use `--cpu_offload` if `accelerate` is installed.
- Reduce `--num_inference_steps`, `--height`, and `--width`.
- Use `--overwrite` only when intentionally replacing an existing `index.jsonl` or image files; by default the runner refuses to overwrite existing outputs.

### StoryDiffusion

Official requirements are in:

```bash
baselines/image/StoryDiffusion/requirements.txt
```

Official low-VRAM interactive command:

```bash
cd baselines/image/StoryDiffusion
python gradio_app_sdxl_specific_id_low_vram.py
```

The official release exposes Notebook/Gradio image generation rather than a stable batch CLI. The local wrapper currently prepares prompt manifests from the unified JSONL input.

### IC-LoRA

The official repository provides training config, model zoo links, and a ComfyUI workflow. To generate images, prepare a ComfyUI FLUX environment with:

- FLUX base model, for example `flux1-dev.safetensors`
- `ali-vilab/In-Context-LoRA` LoRA weights, for example `movie-shots.safetensors`
- `ae.safetensors`
- T5/CLIP text encoders such as `t5xxl_fp8_e4m3fn.safetensors` and `clip_l.safetensors`

The wrapper prepares per-sample workflow JSON files with the unified prompt and seed.

## Commands

DOC/text placeholders:

```bash
python scripts/run_doc.py --input data/input_samples.jsonl --output outputs/text/doc.jsonl
python scripts/run_rolling.py --input data/input_samples.jsonl --output outputs/text/rolling.jsonl
python scripts/run_woig.py --input data/input_samples.jsonl --output outputs/text/woig.jsonl
python scripts/run_womw.py --input data/input_samples.jsonl --output outputs/text/womw.jsonl
```

Image wrappers:

```bash
python scripts/run_sdm_v2.py --input data/input_samples.jsonl --output_dir outputs/image/sdm_v2 --seed 42 --num_inference_steps 10 --height 512 --width 512 --attention_slicing
python scripts/run_storydiffusion.py --input data/input_samples.jsonl --output_dir outputs/image/StoryDiffusion --prepare_only
python scripts/run_iclora.py --input data/input_samples.jsonl --output_dir outputs/image/In-Context-LoRA --prepare_only
python scripts/run_all_baselines.py --input data/input_samples.jsonl
```

SSH GPU SDM-v2 smoke command:

```bash
cd /root/autodl-tmp/baselines/DN-main
export HF_HOME=/root/autodl-tmp/hf-cache
export HF_ENDPOINT=https://hf-mirror.com  # optional mirror when huggingface.co is unreachable
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_sdm_v2.py \
  --input data/input_samples.jsonl \
  --output_dir outputs/image/sdm_v2 \
  --seed 42 \
  --num_inference_steps 10 \
  --height 512 \
  --width 512 \
  --attention_slicing
```

## Smoke Test Results

Executed with:

```bash
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe scripts\run_storydiffusion.py --input data\input_samples.jsonl --output_dir outputs\image\StoryDiffusion --prepare_only --launch_hint
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe scripts\run_iclora.py --input data\input_samples.jsonl --output_dir outputs\image\In-Context-LoRA --prepare_only
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe scripts\run_sdm_v2.py --input data\input_samples.jsonl --output_dir outputs\image\sdm_v2 --local_files_only --num_inference_steps 1 --height 256 --width 256
```

Results:

- StoryDiffusion prepare-only: passed; wrote `outputs/image/StoryDiffusion/index.jsonl`.
- IC-LoRA prepare-only: passed; wrote `outputs/image/In-Context-LoRA/index.jsonl` and per-sample workflow JSON under `outputs/image/In-Context-LoRA/workflows/`.
- SDM-v2 local generation: failed before model loading because `.venv` does not have `diffusers`; local torch is CPU-only (`2.11.0+cpu`) and CUDA is unavailable.
- SDM-v2 SSH GPU dependency check: passed in `/root/autodl-tmp/baselines/sdm_v2_venv`; torch is CUDA-enabled (`2.6.0+cu124`, CUDA 12.4, RTX 4090 visible).
- SDM-v2 SSH GPU smoke generation: blocked before generation; `huggingface.co` was unreachable from the GPU machine and `hf-mirror.com` returned `401 Unauthorized` for `stabilityai/stable-diffusion-2-1-base`. No `sample_001.png` or success index row was written.
- Unified dispatcher: wrote `outputs/baseline_run_summary.json`; exits non-zero while SDM-v2 dependencies are missing.

## Outputs Written

- `data/input_samples.jsonl`
- `outputs/image/StoryDiffusion/index.jsonl`
- `outputs/image/StoryDiffusion/sample_001.prompt.txt`
- `outputs/image/In-Context-LoRA/index.jsonl`
- `outputs/image/In-Context-LoRA/workflows/sample_001.film-storyboard.workflow.json`
- `outputs/baseline_run_summary.json`

No generated image is claimed for StoryDiffusion or IC-LoRA in the current environment; their current outputs are preparation artifacts only.

No generated SDM-v2 image is claimed yet. The expected smoke-test outputs after a successful authorized model load are:

```text
outputs/image/sdm_v2/sample_001.png
outputs/image/sdm_v2/index.jsonl
```

## Required Manual Inputs

- `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN` if Hugging Face requires authentication for SDM-v2 or FLUX-related assets.
- For `stabilityai/stable-diffusion-2-1-base`, accept the Hugging Face model license/agreement with the same account used by the token if the repository is gated.
- CUDA GPU/VRAM for practical SDM-v2, StoryDiffusion, and IC-LoRA generation.
- StoryDiffusion dependency environment if using the official Gradio/Notebook flow.
- ComfyUI + FLUX + IC-LoRA weights for IC-LoRA image generation.
- `OPENAI_API_KEY` only if you later rerun DOC/OpenAI-dependent text generation; it was not used here.

## Full Dataset Run

Replace `data/input_samples.jsonl` with the full dataset JSONL using the same schema, then run:

```bash
python scripts/run_sdm_v2.py --input data/full_dataset.jsonl --output_dir outputs/image/sdm_v2 --seed 42 --num_inference_steps 20 --height 512 --width 512 --attention_slicing
python scripts/run_storydiffusion.py --input data/full_dataset.jsonl --output_dir outputs/image/StoryDiffusion --prepare_only
python scripts/run_iclora.py --input data/full_dataset.jsonl --output_dir outputs/image/In-Context-LoRA --prepare_only
```

For the SSH GPU environment:

```bash
cd /root/autodl-tmp/baselines/DN-main
export HF_HOME=/root/autodl-tmp/hf-cache
export HF_TOKEN=your_huggingface_token
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_sdm_v2.py \
  --input data/full_dataset.jsonl \
  --output_dir outputs/image/sdm_v2 \
  --seed 42 \
  --num_inference_steps 20 \
  --height 512 \
  --width 512 \
  --attention_slicing
```

After installing image-generation dependencies and making the SDM-v2 weights available from Hugging Face or cache, rerun the corresponding wrapper or official workflow to produce actual images and JSONL indexes.

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
| SDM-v2 | Image | https://huggingface.co/stabilityai/stable-diffusion-2-1-base | Official model via Diffusers wrapper | `baselines/image/sdm_v2` | Wrapper supports full JSONL batch generation and low-VRAM flags; local `.venv` lacks `diffusers`; SSH GPU env has dependencies installed and generated a smoke-test image from an SD 2.1 base mirror because `huggingface.co` was unreachable from the GPU host | Passed with `--model_id omeregev/sd-2-1-base-mirror` |
| StoryDiffusion | Image | https://github.com/HVision-NKU/StoryDiffusion | Official code | `baselines/image/StoryDiffusion` | Batch CLI implemented for unified JSONL image/comic generation; writes real images plus `index.jsonl` only after save | Passed SSH GPU smoke test with official default `Unstable` SDXL config |
| IC-LoRA | Image | https://github.com/ali-vilab/In-Context-LoRA | Official repo/workflow | `baselines/image/In-Context-LoRA` | Batch wrapper prepares UI/API workflows and submits them to a running ComfyUI FLUX server; writes success only after the image is downloaded | Passed SSH GPU ComfyUI smoke test |

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

The venv reuses the existing CUDA torch from `/root/miniconda3/envs/dn` (`torch 2.6.0+cu124`) to avoid reinstalling multi-GB CUDA wheels. The model itself is not vendored in this repository. If it is not already cached, expect roughly 5-6 GB of Hugging Face downloads for `stabilityai/stable-diffusion-2-1-base` or a matching SD 2.1 base mirror. If Hugging Face gates the repository, log in with a token that has accepted the model license/agreement.

Low-resource options:

- Use `--dtype float16` only on CUDA.
- Use `--attention_slicing`.
- Use `--cpu_offload` if `accelerate` is installed.
- Reduce `--num_inference_steps`, `--height`, and `--width`.
- Use `--overwrite` only when intentionally replacing an existing `index.jsonl` or image files; by default the runner refuses to overwrite existing outputs.

### StoryDiffusion

Official source:

- GitHub: https://github.com/HVision-NKU/StoryDiffusion
- Local official checkout: `baselines/image/StoryDiffusion`
- Official interactive entrypoints: `gradio_app_sdxl_specific_id_low_vram.py` and `Comic_Generation.ipynb`

Official requirements are in:

```bash
baselines/image/StoryDiffusion/requirements.txt
```

The batch wrapper avoids modifying the official repo and extracts the SDXL image/comic path into:

```bash
scripts/run_storydiffusion.py
scripts/storydiffusion_batch_utils.py
```

The wrapper reads `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN` from the environment through Diffusers/Hugging Face when a model requires authentication. Tokens are not stored in code or documentation.

Working SSH GPU environment used for the smoke test:

```bash
ssh -p 14077 root@connect.cqa1.seetacloud.com
mkdir -p /root/autodl-tmp/baselines
cd /root/autodl-tmp/baselines/DN-main
export HF_HOME=/root/autodl-tmp/hf-cache
export HF_ENDPOINT=https://hf-mirror.com  # optional mirror when huggingface.co is unreachable
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python -m pip install diffusers transformers accelerate safetensors pyyaml pillow
```

Actual smoke-test environment reused the existing `/root/autodl-tmp/baselines/sdm_v2_venv` with CUDA torch from `/root/miniconda3/envs/dn`:

- `torch 2.6.0+cu124`, CUDA 12.4
- `diffusers 0.37.1`
- `transformers 5.7.0`
- `accelerate 1.13.0`
- `safetensors 0.7.0`
- `huggingface_hub 1.12.0`
- `Pillow 12.2.0`
- `PyYAML 6.0.3`

GPU/VRAM used: NVIDIA GeForce RTX 4090, 23.53 GiB visible. The official README says the low-VRAM Gradio path was tested on 24 GB GPU memory and expects roughly more than 20 GB GPU memory; use `--attention_slicing`, `--cpu_offload`, lower resolution, and fewer inference steps for constrained cards.

The wrapper supports `--prepare_only`; without it, it loads a Diffusers SDXL pipeline, installs StoryDiffusion paired self-attention processors, expands each single prompt into deterministic four-frame storyboard prompts when needed, saves frame PNGs, optionally saves a four-panel comic PNG, and writes `index.jsonl` rows with `status: "success"` only after images are saved.

Current limitations:

- Text-only StoryDiffusion path only; reference-image PhotoMaker mode is not exposed in this batch wrapper.
- Up to two characters are supported to match the official low-VRAM Gradio guardrail.
- No video generation, DOC, Rolling, w/oIG, w/oMW, or metric evaluation is included.
- Long prompts can be truncated by CLIP; keep production prompts concise when possible.

### IC-LoRA

Official source:

- GitHub: https://github.com/ali-vilab/In-Context-LoRA
- Hugging Face model zoo: https://huggingface.co/ali-vilab/In-Context-LoRA
- Local official checkout: `baselines/image/In-Context-LoRA`
- Official ComfyUI workflow: `baselines/image/In-Context-LoRA/workflow/film-storyboard.json`

The wrapper is:

```bash
scripts/run_iclora.py
scripts/comfyui_client.py
scripts/iclora_workflow_utils.py
```

It keeps `--prepare_only` behavior and, without `--prepare_only`, converts the ComfyUI UI workflow into API prompt format, submits it to `/prompt`, polls `/history/{prompt_id}`, downloads the produced image through `/view`, saves `outputs/image/In-Context-LoRA/{sample_id}.png`, and writes `index.jsonl`. Rows use `metadata.status: "success"` only after the image file exists and has non-zero size.

Prompt handling is deterministic. If a sample prompt does not already contain `[MOVIE-SHOTS]`, it is converted to:

```text
[MOVIE-SHOTS] {prompt}, [SCENE-1] establishing shot in {scene}..., [SCENE-2] {characters} in a clear character action..., [SCENE-3] cinematic resolution...
```

No external LLM is called.

ComfyUI install path used on the SSH GPU machine:

```bash
/root/autodl-tmp/baselines/ComfyUI
```

Typical install/start commands:

```bash
ssh -p 14077 root@connect.cqa1.seetacloud.com
mkdir -p /root/autodl-tmp/baselines
cd /root/autodl-tmp/baselines
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m pip install -r requirements.txt
python main.py --listen 127.0.0.1 --port 8188
```

Actual setup used `/root/autodl-tmp/baselines/sdm_v2_venv/bin/python`, cloned ComfyUI commit `a7d82ba`, installed `av==14.2.0` from the official PyPI index because the default mirror tried to build `av` from source, and installed the remaining ComfyUI requirements from the configured mirror. The ComfyUI server reported version `0.20.1`.

If you run the batch wrapper outside the GPU host, forward the port first:

```bash
ssh -p 14077 -L 8188:127.0.0.1:8188 root@connect.cqa1.seetacloud.com
```

Required weight files and ComfyUI locations:

- FLUX base model, `flux1-dev.safetensors`: `/root/autodl-tmp/baselines/ComfyUI/models/unet/flux1-dev.safetensors` (23 GB; downloaded from `Comfy-Org/flux1-dev` via `hf-mirror.com`)
- VAE, `ae.safetensors`: `/root/autodl-tmp/baselines/ComfyUI/models/vae/ae.safetensors` (320 MB; downloaded from `camenduru/FLUX.1-dev` via `hf-mirror.com`)
- T5 text encoder, for example `t5xxl_fp8_e4m3fn.safetensors` or `t5xxl_fp16.safetensors`: `ComfyUI/models/clip/`
- T5 text encoder used, `t5xxl_fp8_e4m3fn.safetensors`: `/root/autodl-tmp/baselines/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors` (4.6 GB; downloaded from `comfyanonymous/flux_text_encoders`)
- CLIP text encoder, `clip_l.safetensors`: `/root/autodl-tmp/baselines/ComfyUI/models/clip/clip_l.safetensors` (235 MB; downloaded from `comfyanonymous/flux_text_encoders`)
- IC-LoRA film/storyboard LoRA, `film-storyboard.safetensors`: `/root/autodl-tmp/baselines/ComfyUI/models/loras/film-storyboard.safetensors` (165 MB; downloaded from `ali-vilab/In-Context-LoRA`)
- Workflow compatibility symlink: `/root/autodl-tmp/baselines/ComfyUI/models/loras/movie-shots.safetensors -> film-storyboard.safetensors`

Sources used:

- FLUX/encoder files: ComfyUI-compatible Hugging Face repositories above, because direct `black-forest-labs/FLUX.1-dev` access returned 403 until the account accepts the gated model agreement.
- IC-LoRA weights: `ali-vilab/In-Context-LoRA` Hugging Face repository.

If Hugging Face gates any asset, accept the model agreement/license in the browser for the same account and set one of these environment variables before downloading or running ComfyUI. Do not put tokens in scripts, logs, or README files.

```bash
export HF_TOKEN=your_huggingface_token
# or
export HUGGINGFACE_HUB_TOKEN=your_huggingface_token
```

GPU/VRAM:

- SSH GPU used: NVIDIA GeForce RTX 4090, 24564 MiB total by `nvidia-smi`.
- ComfyUI reported device: `cuda:0 NVIDIA GeForce RTX 4090 : cudaMallocAsync`, `vram_total: 25262096384`, `vram_free: 24850661376` before generation.
- IC-LoRA uses FLUX and the official workflow is 1024x1536, so use a CUDA GPU with roughly 24 GB VRAM or more for practical generation.
- Lower VRAM may require fp8 text encoder, lower resolution, offload, or ComfyUI-specific memory flags.

Current limitation:

- The local machine has CPU-only torch and no `nvidia-smi`.
- Direct `black-forest-labs/FLUX.1-dev` downloads returned 403 for the provided account until the model agreement is accepted; the smoke test used ComfyUI-compatible public mirrors/repos listed above.
- Full `av>=14.2.0` installation from the default mirror tried to build from source and failed; installing the `av==14.2.0` binary wheel from PyPI fixed ComfyUI startup.
- No DOC, Rolling, w/oIG, w/oMW, CLIP/ViCLIP/DINO/VBench, or video evaluation is included.

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
python scripts/run_storydiffusion.py --input data/input_samples.jsonl --output_dir outputs/image/StoryDiffusion --seed 42 --model Unstable --num_inference_steps 20 --height 512 --width 512 --attention_slicing
python scripts/run_iclora.py --input data/input_samples.jsonl --output_dir outputs/image/In-Context-LoRA --seed 42 --workflow baselines/image/In-Context-LoRA/workflow/film-storyboard.json --comfy_url http://127.0.0.1:8188 --max_samples 1 --timeout 900
python scripts/run_iclora.py --input data/input_samples.jsonl --output_dir outputs/image/In-Context-LoRA --seed 42 --workflow baselines/image/In-Context-LoRA/workflow/film-storyboard.json --max_samples 1 --prepare_only
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
  --model_id omeregev/sd-2-1-base-mirror \
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
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_storydiffusion.py --input data/input_samples.jsonl --output_dir outputs/image/StoryDiffusion --model Unstable --seed 42 --num_inference_steps 2 --height 512 --width 512 --max_samples 1 --device cuda --dtype float16 --comic_type "Four Pannel" --attention_slicing
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe -m py_compile scripts\run_iclora.py scripts\comfyui_client.py scripts\iclora_workflow_utils.py
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe scripts\run_iclora.py --input data\input_samples.jsonl --output_dir outputs\image\In-Context-LoRA --seed 42 --workflow baselines\image\In-Context-LoRA\workflow\film-storyboard.json --max_samples 1 --prepare_only
cd /root/autodl-tmp/baselines/ComfyUI
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python main.py --listen 127.0.0.1 --port 8188
cd /root/autodl-tmp/baselines/DN-main
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_iclora.py --input data/input_samples.jsonl --output_dir outputs/image/In-Context-LoRA --seed 42 --workflow baselines/image/In-Context-LoRA/workflow/film-storyboard.json --comfy_url http://127.0.0.1:8188 --max_samples 1 --timeout 1800
C:\Users\User\Desktop\DN-main\.venv\Scripts\python.exe scripts\run_sdm_v2.py --input data\input_samples.jsonl --output_dir outputs\image\sdm_v2 --local_files_only --num_inference_steps 1 --height 256 --width 256
```

Results:

- StoryDiffusion local prepare-only: passed; wrote deterministic prompts to `outputs/image/StoryDiffusion/index.jsonl`.
- StoryDiffusion SSH GPU generation: passed with `--model Unstable` (`stablediffusionapi/sdxl-unstable-diffusers-y` from official `config/models.yaml`); generated four 512x512 frames plus one four-panel comic and wrote one success index row. Model cache size was about 6.5 GB under `/root/autodl-tmp/hf-cache`.
- IC-LoRA wrapper syntax check: passed for `scripts/run_iclora.py`, `scripts/comfyui_client.py`, and `scripts/iclora_workflow_utils.py`.
- IC-LoRA local prepare-only: passed for one row from `data/input_samples.jsonl`; wrote `outputs/image/In-Context-LoRA/index.jsonl`, UI workflow JSON under `outputs/image/In-Context-LoRA/workflows/`, and API prompt JSON under `outputs/image/In-Context-LoRA/api_workflows/`.
- IC-LoRA SSH GPU environment: passed; `nvidia-smi` reported NVIDIA GeForce RTX 4090 with 24564 MiB total VRAM; ComfyUI `/system_stats` reported `pytorch_version: 2.6.0+cu124` and CUDA device `cuda:0`.
- IC-LoRA SSH GPU generation: passed via ComfyUI at `http://127.0.0.1:8188`; generated `outputs/image/In-Context-LoRA/sample_001.png` (about 1.3 MB) and wrote one success row to `outputs/image/In-Context-LoRA/index.jsonl` with prompt id `e923eb96-585a-4b68-a046-61628a092569`.
- SDM-v2 local generation: failed before model loading because `.venv` does not have `diffusers`; local torch is CPU-only (`2.11.0+cpu`) and CUDA is unavailable.
- SDM-v2 SSH GPU dependency check: passed in `/root/autodl-tmp/baselines/sdm_v2_venv`; torch is CUDA-enabled (`2.6.0+cu124`, CUDA 12.4, RTX 4090 visible).
- SDM-v2 SSH GPU official model check: token authentication succeeded, but `huggingface.co` was unreachable from the GPU machine and `hf-mirror.com` did not expose `stabilityai/stable-diffusion-2-1-base`.
- SDM-v2 SSH GPU smoke generation: passed with `--model_id omeregev/sd-2-1-base-mirror`; downloaded about 5.16 GB into `/root/autodl-tmp/hf-cache`, generated one 512x512 image, and wrote one success index row.
- Unified dispatcher: wrote `outputs/baseline_run_summary.json`; exits non-zero while SDM-v2 dependencies are missing.

## Outputs Written

- `data/input_samples.jsonl`
- `outputs/image/StoryDiffusion/index.jsonl`
- `outputs/image/StoryDiffusion/sample_001.prompt.txt`
- `outputs/image/StoryDiffusion/sample_001.png`
- `outputs/image/StoryDiffusion/sample_001_frame_001.png`
- `outputs/image/StoryDiffusion/sample_001_frame_002.png`
- `outputs/image/StoryDiffusion/sample_001_frame_003.png`
- `outputs/image/StoryDiffusion/sample_001_frame_004.png`
- `outputs/image/In-Context-LoRA/sample_001.png`
- `outputs/image/In-Context-LoRA/index.jsonl`
- `outputs/image/In-Context-LoRA/workflows/sample_001.film-storyboard.workflow.json`
- `outputs/image/In-Context-LoRA/api_workflows/sample_001.film-storyboard.api.json`
- `outputs/image/sdm_v2/sample_001.png`
- `outputs/image/sdm_v2/index.jsonl`
- `outputs/baseline_run_summary.json`

Generated StoryDiffusion and IC-LoRA smoke-test outputs were synced back from the SSH GPU machine.

Generated StoryDiffusion smoke-test outputs:

```text
outputs/image/StoryDiffusion/sample_001.png
outputs/image/StoryDiffusion/sample_001_frame_001.png
outputs/image/StoryDiffusion/sample_001_frame_002.png
outputs/image/StoryDiffusion/sample_001_frame_003.png
outputs/image/StoryDiffusion/sample_001_frame_004.png
outputs/image/StoryDiffusion/index.jsonl
```

Generated SDM-v2 smoke-test outputs:

```text
outputs/image/sdm_v2/sample_001.png
outputs/image/sdm_v2/index.jsonl
```

Generated IC-LoRA smoke-test outputs:

```text
outputs/image/In-Context-LoRA/sample_001.png
outputs/image/In-Context-LoRA/index.jsonl
outputs/image/In-Context-LoRA/workflows/sample_001.film-storyboard.workflow.json
outputs/image/In-Context-LoRA/api_workflows/sample_001.film-storyboard.api.json
```

The `index.jsonl` row records `status: "success"` only after the image file is saved.

## Required Manual Inputs

- `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN` if Hugging Face requires authentication for SDM-v2, StoryDiffusion SDXL, or FLUX-related assets.
- For `stabilityai/stable-diffusion-2-1-base` or `black-forest-labs/FLUX.1-dev`, accept the Hugging Face model license/agreement with the same account used by the token if the repository is gated.
- CUDA GPU/VRAM for practical SDM-v2, StoryDiffusion, and IC-LoRA generation.
- StoryDiffusion dependency environment if using either the batch CLI or the official Gradio/Notebook flow.
- ComfyUI + FLUX + IC-LoRA weights for IC-LoRA image generation, with the server listening at the `--comfy_url` passed to `scripts/run_iclora.py`.
- `OPENAI_API_KEY` only if you later rerun DOC/OpenAI-dependent text generation; it was not used here.

## Full Dataset Run

Replace `data/input_samples.jsonl` with the full dataset JSONL using the same schema, then run:

```bash
python scripts/run_sdm_v2.py --input data/full_dataset.jsonl --output_dir outputs/image/sdm_v2 --seed 42 --num_inference_steps 20 --height 512 --width 512 --attention_slicing
python scripts/run_storydiffusion.py --input data/full_dataset.jsonl --output_dir outputs/image/StoryDiffusion --seed 42 --model Unstable --num_inference_steps 20 --height 512 --width 512 --attention_slicing
python scripts/run_iclora.py --input data/full_dataset.jsonl --output_dir outputs/image/In-Context-LoRA --seed 42 --workflow baselines/image/In-Context-LoRA/workflow/film-storyboard.json --comfy_url http://127.0.0.1:8188 --timeout 900
```

For the SSH GPU environment:

```bash
cd /root/autodl-tmp/baselines/DN-main
export HF_HOME=/root/autodl-tmp/hf-cache
export HF_TOKEN=your_huggingface_token
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_sdm_v2.py \
  --input data/full_dataset.jsonl \
  --output_dir outputs/image/sdm_v2 \
  --model_id omeregev/sd-2-1-base-mirror \
  --seed 42 \
  --num_inference_steps 20 \
  --height 512 \
  --width 512 \
  --attention_slicing

/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_storydiffusion.py \
  --input data/full_dataset.jsonl \
  --output_dir outputs/image/StoryDiffusion \
  --model Unstable \
  --seed 42 \
  --num_inference_steps 20 \
  --height 512 \
  --width 512 \
  --device cuda \
  --dtype float16 \
  --comic_type "Four Pannel" \
  --attention_slicing

# In another SSH session, from /root/autodl-tmp/baselines/ComfyUI:
python main.py --listen 127.0.0.1 --port 8188

cd /root/autodl-tmp/baselines/DN-main
/root/autodl-tmp/baselines/sdm_v2_venv/bin/python scripts/run_iclora.py \
  --input data/full_dataset.jsonl \
  --output_dir outputs/image/In-Context-LoRA \
  --seed 42 \
  --workflow baselines/image/In-Context-LoRA/workflow/film-storyboard.json \
  --comfy_url http://127.0.0.1:8188 \
  --timeout 900
```

After installing image-generation dependencies and making the SDM-v2, StoryDiffusion SDXL, or IC-LoRA FLUX weights available from Hugging Face or cache, rerun the corresponding wrapper to produce actual images and JSONL indexes.

# Remote Baseline Status - 2026-04-29

## Current Goal

Run the newly selected baselines on the AutoDL RTX 4090 machine using the same
DN-style benchmark subsets and save comparable JSON/image artifacts.

## Completed

- Local baseline repos are present under `baselines/`:
  - `DOC`
  - `StoryDiffusion`
  - `IC-LoRA`
- SDM-v2 is represented by a Diffusers runner using
  `stabilityai/stable-diffusion-2-1-base`; the requested Stability-AI GitHub URL
  was not cloneable.
- DN-style subsets are prepared:
  - `baselines/subsets/dn_style_smoke3.json`
  - `baselines/subsets/dn_style_formal8.json`
- Unified runner scaffold is prepared:
  - `scripts/baselines/baseline_io.py`
  - `scripts/baselines/run_storydiffusion.py`
  - `scripts/baselines/run_sdmv2.py`
  - `scripts/baselines/run_iclora.py`
  - `scripts/baselines/summarize_image_baselines.py`
- Remote StoryDiffusion environment was installed and verified:
  - `torch==2.0.1+cu118`
  - CUDA available
  - GPU detected as NVIDIA GeForce RTX 4090
  - `diffusers==0.25.0`
  - `transformers==4.36.2`
  - `xformers==0.0.20`

## Not Yet Complete

- StoryDiffusion smoke3 has not been confirmed successful.
  - The first run failed because direct access to `huggingface.co` was blocked.
  - The runner was patched to skip unused PhotoMaker eager download in textual
    mode.
  - Remote env scripts were updated to use `HF_ENDPOINT=https://hf-mirror.com`.
  - A replacement SDXL smoke run was launched, but SSH access later stopped
    returning a valid SSH banner, so the final status is unverified.
- StoryDiffusion formal8 has not been run or confirmed.
- SDM-v2 remote env has not been confirmed installed.
- SDM-v2 smoke3/formal8 have not been run.
- IC-LoRA is only a structured blocker placeholder; no ComfyUI workflow or real
  image generation has been completed.
- DOC/Rolling/w/oIG/w/oMW text baselines have not been run.
- No cross-baseline summary table is ready for paper use.

## Current Blocker

Remote SSH became unavailable from the local machine:

```text
Error reading SSH protocol banner
ssh: connect to host connect.westb.seetacloud.com port 19498: Connection timed out
```

The TCP port intermittently appears open, but it does not consistently return an
SSH banner. This blocks checking the launched StoryDiffusion process, logs, GPU
state, and output files.

## Next Commands After SSH Recovers

```bash
cd /root/autodl-tmp/DN
bash scripts/baselines/remote_status_check.sh
```

If StoryDiffusion smoke3 succeeded:

```bash
bash scripts/baselines/remote_run_image_baselines.sh story-formal
```

If StoryDiffusion smoke3 did not finish:

```bash
bash scripts/baselines/remote_run_image_baselines.sh story-smoke
```

After StoryDiffusion is stable:

```bash
bash scripts/baselines/remote_sdmv2_setup.sh
bash scripts/baselines/remote_run_image_baselines.sh sdm-smoke
bash scripts/baselines/remote_run_image_baselines.sh sdm-formal
```

## Completion Judgment

- Framework readiness: mostly complete.
- StoryDiffusion environment readiness: high, but final smoke output unverified.
- Actual image baseline result readiness: not yet paper-ready.
- Most likely next deliverable: StoryDiffusion smoke3 plus formal8 once remote
  SSH access is restored.

## Update - 2026-04-30

### Completed real generation

- StoryDiffusion smoke3 completed successfully:
  - remote output: `/root/autodl-tmp/outputs/storydiffusion_smoke3/storydiffusion_smoke3_unstable_20260430_1128`
  - local copy: `remote_baseline_results_20260430/outputs/storydiffusion_smoke3/storydiffusion_smoke3_unstable_20260430_1128`
  - success: 3/3
  - images: 4 per sample
  - mean latency: 9.088s
  - p95 latency: 11.152s
  - model source: `stablediffusionapi/sdxl-unstable-diffusers-y`
  - settings: 512x512, 6 steps, textual-description mode
- StoryDiffusion formal8 completed successfully:
  - remote output: `/root/autodl-tmp/outputs/storydiffusion_formal8/storydiffusion_formal8_unstable_20260430_1131`
  - local copy: `remote_baseline_results_20260430/outputs/storydiffusion_formal8/storydiffusion_formal8_unstable_20260430_1131`
  - success: 8/8
  - images: 4 per sample
  - mean latency: 8.053s
  - p95 latency: 10.036s
  - model source: `stablediffusionapi/sdxl-unstable-diffusers-y`
  - settings: 512x512, 6 steps, textual-description mode

### Completed fallback sanity generation

- Public SD fallback smoke3/formal8 completed with `CompVis/stable-diffusion-v1-4`.
- These runs are useful for checking the generic Diffusers runner and output
  format, but they are not the strict selected `stable-diffusion-2-1-base /
  SDM-v2` baseline.

### Still blocked

- Strict SDM-v2 (`stabilityai/stable-diffusion-2-1-base`) is still blocked:
  - `hf-mirror.com` returns 401 for the model metadata.
  - The model is not cached locally.
  - A Hugging Face token with accepted StabilityAI license, or a manually
    supplied local model snapshot, is needed for the strict run.
- IC-LoRA remains blocked:
  - ComfyUI workflow is not configured.
  - IC-LoRA weights are not downloaded/placed.
  - No training was attempted.
- Text baselines remain not run:
  - DOC is cloned only.
  - Rolling / w/oIG / w/oMW still need config-level implementation and runs.

### Downloaded result package

- Local package: `remote_baseline_results_20260430/DN-baseline-results-lite-20260430.tar.gz`
- Local summary: `remote_baseline_results_20260430/outputs/image_baseline_summary_20260430.csv`
- Local blocker report: `remote_baseline_results_20260430/outputs/failure_report_20260430.md`

## Update - 2026-04-30 Formal20 Expansion

### StoryDiffusion formal20 completed

- Subset file: `baselines/subsets/dn_style_formal20.json`
- Remote output: `/root/autodl-tmp/outputs/storydiffusion_formal20/storydiffusion_formal20_unstable_20260430_1200`
- Local copy: `remote_baseline_results_20260430/outputs/storydiffusion_formal20/storydiffusion_formal20_unstable_20260430_1200`
- Success: 20/20
- Images: 80 total, 4 per sample
- Mean latency: 7.69s
- p95 latency: 8.415s
- Settings: 512x512, 6 steps, textual-description mode
- Model source: `stablediffusionapi/sdxl-unstable-diffusers-y`
- Downloaded package: `remote_baseline_results_20260430/DN-storydiffusion-formal20-20260430.tar.gz`
- Expanded summary: `remote_baseline_results_20260430/outputs/storydiffusion_expanded_summary_20260430.csv`

### Formal8 image quality check completed

- Quality folder: `remote_baseline_results_20260430/quality_checks`
- Contact sheet: `remote_baseline_results_20260430/quality_checks/formal8_contact_sheet.png`
- Auto metrics: `remote_baseline_results_20260430/quality_checks/formal8_image_quality_auto.csv`
- Manual report: `remote_baseline_results_20260430/quality_checks/formal8_quality_report.md`
- Auto quality checks found no black/blank/corrupt/tiny images.
- Manual inspection conclusion: technically successful but semantically weak.
  Many unrelated themes collapse into similar lantern-lit East-Asian
  street/interior imagery. Use as execution/efficiency evidence, but add
  semantic-alignment caveats before using in a paper-facing visual-quality table.

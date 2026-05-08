# image_baselines_smoke_and_formal8

这些目录保留为 smoke / formal8 / blocker / fallback 历史证据，不应与 formal20 主结果混用。

- `StoryDiffusion smoke3`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/storydiffusion_smoke3/storydiffusion_smoke3_unstable_20260430_1128`
  - sample_size: `3`; success_count: `3`; success_rate: `1.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: StoryDiffusion low-VRAM textual-description mode; 4 DN-style scene prompts per item by default.

- `StoryDiffusion formal8`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/storydiffusion_formal8/storydiffusion_formal8_unstable_20260430_1131`
  - sample_size: `8`; success_count: `8`; success_rate: `1.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: StoryDiffusion low-VRAM textual-description mode; 4 DN-style scene prompts per item by default.

- `SDM-v2 strict smoke3 blocker`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/sdmv2_smoke3/sdmv2_smoke3_blocker_20260429`
  - sample_size: `3`; success_count: `0`; success_rate: `0.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: SDM-v2 model load blocked before generation; likely gated model access or network/cache issue.

- `SD public v1-4 smoke3 fallback`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/sd_public_v14_smoke3/sdmv2_smoke3_compvis_v14_20260430_1135`
  - sample_size: `3`; success_count: `3`; success_rate: `1.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: SDM-v2 uses diffusers and generates one image per DN-style item; no character-consistency claim.

- `SD public v1-4 formal8 fallback`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/sd_public_v14_formal8/sdmv2_formal8_compvis_v14_20260430_1142`
  - sample_size: `8`; success_count: `8`; success_rate: `1.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: SDM-v2 uses diffusers and generates one image per DN-style item; no character-consistency claim.

- `IC-LoRA smoke3 blocker`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_smoke3/ic-lora_smoke3_check`
  - sample_size: `3`; success_count: `0`; success_rate: `0.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: IC-LoRA smoke currently records workflow/model blocker only; no training is attempted.

- `IC-LoRA formal8 probe`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_formal8_probe/ic-lora_probe_20260430_formal8`
  - sample_size: `8`; success_count: `0`; success_rate: `0.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: IC-LoRA readiness probe only; records concrete workflow, asset, and ComfyUI blockers before any training or real inference.

- `IC-LoRA formal8 real`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_formal8_real/ic-lora_real_20260430_formal8`
  - sample_size: `8`; success_count: `8`; success_rate: `1.0`
  - primary_use: historical / debugging / early evidence
  - reproducible: `case-by-case`
  - notes: IC-LoRA attempts official ComfyUI workflow execution when assets and ComfyUI API are ready.

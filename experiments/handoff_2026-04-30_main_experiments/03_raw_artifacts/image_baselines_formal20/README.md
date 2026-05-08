# image_baselines_formal20

正式图像 baseline 主实验 raw artifact 索引。这些目录是当前 image formal20 ground truth。

- `StoryDiffusion first_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/storydiffusion_formal20/storydiffusion_formal20_unstable_20260430_1200`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: StoryDiffusion low-VRAM textual-description mode; 4 DN-style scene prompts per item by default.

- `StoryDiffusion next_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/storydiffusion_nextturn_formal20/storydiffusion_nextturn_formal20_unstable_v2_20260430`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: StoryDiffusion next-turn latency measures the post-click continuation image only.

- `SDM-v2 first_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/sdmv2_local_formal20/sdmv2_sdmv2_local_formal20_20260430`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: SDM-v2 uses diffusers and generates one image per DN-style item; no character-consistency claim.

- `SDM-v2 next_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/sdmv2_nextturn_formal20/sdmv2_sdmv2_nextturn_formal20_20260430`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: SDM-v2 next-turn latency measures the post-click continuation image only.

- `IC-LoRA first_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_formal20_real/ic-lora_real_20260430_formal20`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: IC-LoRA attempts official ComfyUI workflow execution when assets and ComfyUI API are ready.

- `IC-LoRA next_turn formal20`
  - source: `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_nextturn_formal20_real/ic-lora_real_20260430_nextturn_formal20`
  - sample_size: `20`; success_count: `20`; success_rate: `1.0`
  - primary_use: main result
  - reproducible: `yes`, via current runner and remote 4090 env
  - notes: IC-LoRA next-turn latency measures the post-click continuation workflow only.

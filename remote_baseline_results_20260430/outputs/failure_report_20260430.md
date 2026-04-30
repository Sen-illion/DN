# Baseline Failure / Blocker Report - 2026-04-30

## Completed real generation

- StoryDiffusion smoke3: success 3/3, model source `stablediffusionapi/sdxl-unstable-diffusers-y`, 512x512, 6 steps, 4 images/sample.
- StoryDiffusion formal8: success 8/8, model source `stablediffusionapi/sdxl-unstable-diffusers-y`, 512x512, 6 steps, 4 images/sample.
- Public SD sanity fallback smoke3/formal8: success, model `CompVis/stable-diffusion-v1-4`. This is not the selected SDM-v2 baseline; it is only a public fallback sanity run.

## Still blocked

- Strict SDM-v2 (`stabilityai/stable-diffusion-2-1-base`) is blocked by model access: hf-mirror returns 401 and the model is not cached locally.
- IC-LoRA is blocked because ComfyUI workflow and model weights are not configured; no training attempted.

## Notes

- StoryDiffusion initially failed on PhotoMaker eager download and incomplete SDXL cache. The DN runner now skips unused PhotoMaker in textual mode and uses the fully downloaded `Unstable` SDXL-compatible model snapshot.
- StoryDiffusion formal8 is the closest current image-baseline deliverable.

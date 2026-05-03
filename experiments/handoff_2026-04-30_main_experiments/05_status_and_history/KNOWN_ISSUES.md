# Known Issues

- StoryDiffusion and ComfyUI historically competed for RTX 4090 VRAM during next-turn runs; StoryDiffusion next-turn only stabilized after ComfyUI was stopped and later restarted.
- Official `stabilityai/stable-diffusion-2-1-base` access was blocked/down; the runnable SDM-v2 path was repaired through a local model directory workflow instead of direct online access.
- DOC baseline is currently useful through a faithful fallback adapter and normalized artifact path; upstream DOC full GPT3/Alpa/OPT stack is not fully reproduced in this repo.
- Some inherited Chinese text fields are mojibake/garbled in upstream artifacts and status docs.
- Two local review images were previously corrupted during sync and now have explicit redownload replacements.
- `image_baseline_summary_20260430.csv` mixes early blocker/fallback rows with successful rows; it should not be mistaken for the final formal20 comparison table.
- DN next-turn benchmarking cannot use `PREGENERATION_ENABLED=false` as a clean “normal” control: that path can fall back to placeholder scene handling instead of a faithful production continuation, so the strict DN `normal20` measurement uses the production pregeneration path with `read_wait_s = 0`.

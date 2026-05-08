# Baseline Image From DN Text Report

Run directory: `outputs/baseline_image_from_dn_text/run_20260430_144923`

## Overall Summary

| baseline | status | generated | comparable | scored | DN avg | baseline avg | delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iclora | unavailable | 0/100 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 |
| sdm_v2 | completed | 100/100 | 77 | 77 | 4.6753 | 1.3139 | -3.3614 |
| storydiffusion | unavailable | 0/100 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 |

## Notes

- SDM-v2 generated 100/100 images from text-only inputs; 77 segments had DN reference images available for comparison.
- DN reference PNGs were missing for 23 segments, so those samples could not be scored against DN.
- iclora: Requires ComfyUI + FLUX + IC-LoRA weights; local wrapper prepares workflows only, no image generation was run.
- storydiffusion: Official workflow is Gradio/Notebook-oriented; local wrapper prepares manifests only, no batch image CLI was run.

## Theme Scores (SDM-v2)

| theme | scored | DN avg | baseline avg | delta |
| --- | ---: | ---: | ---: | ---: |
| theme_001_game_1776417898_zthbu3 | 10 | 4.9667 | 1.1500 | -3.8167 |
| theme_002_game_1776418186_406ktb | 4 | 4.3333 | 1.7500 | -2.5833 |
| theme_003_game_1776418475_uho8y4 | 10 | 4.5833 | 1.2000 | -3.3833 |
| theme_004_game_1776418746_kox2ae | 10 | 4.4000 | 1.6667 | -2.7333 |
| theme_005_game_1776419026_gflx4b | 10 | 4.9167 | 1.1500 | -3.7667 |
| theme_006_game_1776419299_05783f | 1 | 5.0000 | 1.6667 | -3.3333 |
| theme_012_game_1776419613_9xv3kl | 10 | 4.9000 | 1.5000 | -3.4000 |
| theme_018_game_1776419881_ts9erz | 10 | 4.5500 | 1.2333 | -3.3167 |
| theme_054_game_1776420257_ds08b3 | 2 | 4.6667 | 1.0000 | -3.6667 |
| theme_073_game_1776420517_nejnnv | 10 | 4.5167 | 1.1500 | -3.3667 |

# Sample Guide

## `formal20_quality_review`
Each review sheet is organized as:
- rows: `first_turn`, `next_turn current`, `next_turn next`
- columns: `StoryDiffusion`, `SDM-v2`, `IC-LoRA`

Representative sample IDs:
- `DNQBV1_001`
- `DNQBV1_005`
- `DNQBV1_010`
- `DNQBV1_015`
- `DNQBV1_020`

## What to inspect
- continuity: compare `next_turn current` to `next_turn next`
- first-turn visual quality: inspect the `first_turn` row
- baseline behavior differences: compare the same row across three columns

## Known image replacement notes
- original damaged local file:
  - `D:/Projects/DN/remote_baseline_results_20260430/outputs/sdmv2_nextturn_formal20/sdmv2_sdmv2_nextturn_formal20_20260430/DNQBV1_009/image_001.png`
- replacement file used for review:
  - `D:/Projects/DN/remote_baseline_results_20260430/outputs/sdmv2_nextturn_formal20/sdmv2_sdmv2_nextturn_formal20_20260430/DNQBV1_009/image_001_redownload.png`

- original damaged local file:
  - `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_nextturn_formal20_real/ic-lora_real_20260430_nextturn_formal20/DNQBV1_007/ICLORA_NEXT_DNQBV1_007_00001_.png`
- replacement file used for review:
  - `D:/Projects/DN/remote_baseline_results_20260430/outputs/iclora_nextturn_formal20_real/ic-lora_real_20260430_nextturn_formal20/DNQBV1_007/ICLORA_NEXT_DNQBV1_007_00001__redownload.png`

## Encoding caveat
Some inherited Chinese metadata fields are mojibake/garbled in upstream artifacts. This affects captions and some text fields, but not the image files themselves.

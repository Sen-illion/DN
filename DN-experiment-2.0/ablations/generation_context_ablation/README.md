# Generation Context Ablation

This directory contains the dedicated image-generation-stage context ablation for DN.
It only targets the generation input context sent to the image model.
It does not implement evaluator-input ablations, protagonist-reference-count ablations, or prompt-optimizer on/off ablations.

## What is ablated

Three generation-context groups are implemented:

1. `prompt_only`
   - Use the stored LLM-generated image prompt from the source segment JSON.
   - Do not pass the previous scene image.

2. `prev_image_only`
   - Use the previous scene image as the primary continuity context.
   - Do not use the full LLM-rich prompt.
   - Keep a minimal base instruction so the image API remains callable.

3. `prompt_plus_prev_image`
   - Use the stored LLM-generated image prompt.
   - Also pass the previous scene image.

## Directory layout

- `common.py`: dataset discovery, manifest building, and workbook helpers.
- `build_generation_context_dataset.py`: build the ablation dataset manifest from `game_themes_100.json` and `DN-experiment-2.0/theme_*` source runs.
- `run_generation_context_ablation.py`: run generation, reuse multiview scoring, aggregate outputs, and export the final workbook.
- `configs/context_ablation_config.json`: group definitions, scale presets, and runtime defaults.
- `configs/scoring_config.json`: scoring dimensions and weights reused by aggregation.
- `outputs/datasets/...`: dataset manifests in JSON, JSONL, and Excel.
- `outputs/runs/...`: generation outputs, scoring outputs, summaries, and final Excel workbooks.

## Dataset construction

The dataset builder:

- reads `C:\Users\User\Desktop\DN-main\game_themes_100.json`
- discovers source games under `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\theme_*`
- keeps only contiguous segments with:
  - a current source scene text
  - a current stored source prompt
  - a current source image
  - a previous-segment source image
- expands each selected `(theme, game, segment)` into all three ablation groups so the groups use the same evaluation slice
- exports:
  - `dataset_manifest.json`
  - `dataset_manifest.jsonl`
  - `dataset_manifest.xlsx`
  - `dataset_manifest.prompt_only.{json,jsonl,xlsx}`
  - `dataset_manifest.prev_image_only.{json,jsonl,xlsx}`
  - `dataset_manifest.prompt_plus_prev_image.{json,jsonl,xlsx}`

## Example commands

Build only the dataset manifest:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\build_generation_context_dataset.py `
  --scale pilot `
  --seed 42
```

Build a per-theme dataset slice with 4 evaluation segments:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\build_generation_context_dataset.py `
  --scale full `
  --seed 42 `
  --theme-ids 1 `
  --max-games 1 `
  --max-eval-segments 4
```

Dry-run the full runner with auto-built dataset:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --scale pilot `
  --seed 42 `
  --max-games 1 `
  --max-eval-segments 1 `
  --dry-run
```

Run the full experiment with judge models:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --scale pilot `
  --seed 42 `
  --judge-models gpt-4o
```

Run generation only for one already-built dataset slice:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --dataset-manifest C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\datasets\generation_context_ablation_full_seed42_theme001\dataset_manifest.json `
  --run-name theme001_round4_generation `
  --skip-scoring
```

After several generation-only runs finish, score them together:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\score_generation_context_ablation_runs.py `
  --run-dirs `
    C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\runs\theme001_round4_generation `
    C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\runs\theme003_round4_generation `
    C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\runs\theme004_round4_generation `
  --judge-models gpt-4o `
  --batch-name themes001_003_004_round4_scored
```

## Final workbook

The runner writes `generation_context_ablation_results.xlsx` with these sheets:

- `dataset_manifest`
- `generation_runs`
- `per_sample_results`
- `group_summary`
- `group_comparison`
- `failure_cases`
- `config_snapshot`

## Reused existing logic

- Generation path reuse: `src/image/api_providers.py`
- Source experiment structure reuse: `DN-experiment-2.0/generate_images_from_experiment_json.py`
- Judge scoring reuse: `DN-experiment-2.0/图片一致性_experiment/multiview_image_consistency/scripts/score_image_consistency_per_game.py`
- Aggregation reuse: `DN-experiment-2.0/图片一致性_experiment/multiview_image_consistency/scripts/aggregate_multiview_results.py`

## Notes

- The runner creates warmup generations for earlier segments in the chain so `prev_image_only` and `prompt_plus_prev_image` can consume the previous generated image before evaluating later segments.
- The public generation hook is intentionally small: `src/image/api_providers.py` now accepts `_scene_generation_overrides` in `global_state` so the ablation runner can switch prompt strategy and previous-image usage without changing the main evaluator pipeline.
- For actual generation and judge scoring, valid image-generation API credentials and judge-model API access are still required.

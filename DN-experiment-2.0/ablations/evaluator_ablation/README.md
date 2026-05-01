# Evaluator Ablation for Multi-View Image Consistency

This directory contains a self-contained evaluator-ablation workflow for the DN image consistency experiment.
It only changes the evaluator side. It does not change image generation, prompt optimization, protagonist reference count, or other ablation types.

## Scope

Question:
- On the same fixed batch of image-consistency samples, how much do the final consistency scores change when we swap evaluator models or evaluator combinations?

Changed variable:
- evaluator model / evaluator group

Fixed controls:
- same source themes from `game_themes_100.json`
- same reused generated images under `DN-experiment-2.0/theme_*`
- same sample manifest for all judge groups
- same score schema imported from the existing `multiview_image_consistency` scorer

## Directory Layout

- `configs/evaluator_ablation_config.json`: dataset presets, source paths, and required judge groups
- `scripts/shared.py`: shared paths, JSON helpers, legacy scorer loading, workbook export hook
- `scripts/build_evaluator_ablation_dataset.py`: builds the evaluator-ablation dataset manifest from `game_themes_100.json` and existing generated images
- `scripts/run_evaluator_ablation.py`: reuses existing judge outputs and/or scores missing sample-model pairs, then aggregates group differences
- `scripts/export_evaluator_ablation_workbook.mjs`: exports `.xlsx` workbooks with the required sheets via `@oai/artifact-tool`
- `results/`: generated manifests, JSONL, summaries, and Excel workbooks

## What the Dataset Builder Does

Inputs:
- `C:\Users\User\Desktop\DN-main\game_themes_100.json`
- `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\theme_*\*_image_paths.json`
- segment JSON files and existing image files under each `theme_*` folder

Behavior:
- indexes all 100 themes from `game_themes_100.json`
- reuses existing generated images first
- marks every row as available/unavailable and selected/not-selected
- records a concrete `selection_reason` or `availability_reason`
- supports reproducible sampling with fixed seed
- supports preset sizes: `pilot`, `standard`, `full`
- supports manual overrides with `--max-themes`, `--max-games`, `--segments-per-game`, `--max-samples`
- exports JSON, JSONL, and Excel
- emits diagnostics about missing manifests, missing images, and themes without reusable samples

Manifest columns include at least:
- `theme_id`
- `theme`
- `game_id`
- `segment_index`
- `sample_id`
- `image_path`
- `is_available`
- `selection_reason`

## What the Runner Does

Supported required judge groups:
- `gpt-4o`
- `claude-sonnet-4-20250514`
- `gpt-4o + claude-sonnet-4-20250514`
- `gpt-4o + claude-sonnet-4-20250514 + gemini-2.5-flash`

Behavior:
- runs all judge groups on the same selected dataset samples
- reuses existing raw judge JSONL first
- optionally fills missing sample-model pairs with the legacy scorer via `--score-missing`
- writes raw judge rows, per-sample group results, summaries, group comparisons, disagreement analysis, and Excel

## Excel Outputs

Dataset workbook sheets:
- `dataset_manifest`
- `run_metadata`
- `theme_summary`
- `diagnostics`

Evaluator ablation workbook sheets:
- `dataset_manifest`
- `run_metadata`
- `per_sample_results`
- `per_group_summary`
- `group_comparison`
- `disagreement_analysis`

## Metrics

The runner exports at least:
- `overall_score_mean`
- per-dimension means
- `judge_disagreement_mean`
- `valid_sample_count`
- `coverage`
- `judge_models`
- `runtime_seconds_total` when available

## Example Commands

Build a pilot dataset:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\scripts\build_evaluator_ablation_dataset.py `
  --size pilot
```

Build a larger standard dataset:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\scripts\build_evaluator_ablation_dataset.py `
  --size standard `
  --seed 20260425
```

Build with manual caps:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\scripts\build_evaluator_ablation_dataset.py `
  --max-themes 6 `
  --max-games 6 `
  --segments-per-game 3 `
  --max-samples 18 `
  --seed 7
```

Run evaluator ablation by reusing existing judge outputs only:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\scripts\run_evaluator_ablation.py `
  --dataset-json C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_dataset_manifest.json `
  --score-jsonl C:\Users\User\Desktop\DN-main\DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\results\latest_per_game_image_scores.jsonl `
  --dry-run
```

Run evaluator ablation and score missing sample-model pairs if needed:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\scripts\run_evaluator_ablation.py `
  --dataset-json C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_dataset_manifest.json `
  --score-jsonl C:\Users\User\Desktop\DN-main\DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\results\latest_per_game_image_scores.jsonl `
  --score-missing
```

## Current Smoke Test Result

Executed on 2026-04-25 (pilot dataset, reuse-only):
- dataset builder succeeded
- selected 8 samples from 4 themes / 4 games
- reused existing raw judge results from the legacy multiview experiment
- no missing sample-model pairs for the required judge groups
- Excel workbook export succeeded

Current latest outputs:
- dataset manifest JSON: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_dataset_manifest.json`
- dataset manifest Excel: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_dataset_manifest.xlsx`
- ablation summary JSON: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_evaluator_ablation_summary.json`
- ablation workbook Excel: `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\evaluator_ablation\results\latest_evaluator_ablation.xlsx`

## Notes / Limitations

- The current repo only has reusable image manifests for 10 of the 100 themes, so `full` currently means all reusable samples currently available in the repo, not all 100 themes.
- If you need fresh scoring instead of reusing the legacy JSONL, the environment must provide valid evaluator API keys and network access for the configured judge endpoint.
- A local `node_modules/@oai/artifact-tool` junction is created under this ablation directory on first workbook export so the workbook builder can use the bundled spreadsheet runtime cleanly.

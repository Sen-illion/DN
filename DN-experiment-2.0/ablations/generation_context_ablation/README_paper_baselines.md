# Paper Image Consistency Baselines

This setup creates no-GPU, no-Replicate image-consistency baselines from the existing DN source games.
It does not download model checkpoints. It reuses the same configured image API as DN and changes only the prompt/context sent to that API.

## Groups

- `naive_t2i`: current scene text only; weakest baseline.
- `prompt_only_memory`: stored rich DN image prompt only; recommended fair baseline.
- `visual_bible`: fixed text-only visual bible plus current scene; stronger no-GPU memory baseline.
- `prompt_plus_prev_image`: rich prompt plus previous generated image; reference ablation, still without protagonist reference images.

The source DN images under `DN-experiment-2.0/theme_*` are the comparison target for "ours".

## Build Dataset Manifest Only

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\build_generation_context_dataset.py `
  --config C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\configs\paper_baseline_config.json `
  --scale standard `
  --seed 42 `
  --theme-ids 1,2,3,4,5,6,12,18,54,73 `
  --max-games 10 `
  --max-eval-segments 5
```

## Dry Run

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --config C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\configs\paper_baseline_config.json `
  --scale standard `
  --seed 42 `
  --theme-ids 1,2,3,4,5,6,12,18,54,73 `
  --max-games 10 `
  --max-eval-segments 5 `
  --run-name paper_baselines_dry_run `
  --dry-run
```

## Generate Baseline Images

This calls the configured image API and may cost money.

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --config C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\configs\paper_baseline_config.json `
  --scale standard `
  --seed 42 `
  --theme-ids 1,2,3,4,5,6,12,18,54,73 `
  --max-games 10 `
  --max-eval-segments 5 `
  --run-name paper_baselines_10themes_5segments `
  --skip-scoring
```

Outputs are written to:

```text
C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\runs\paper_baselines_10themes_5segments
```

## Score DN Ours

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\scripts\score_image_consistency_per_game.py `
  --experiment-root C:\Users\User\Desktop\DN-main\DN-experiment-2.0 `
  --output-dir C:\Users\User\Desktop\DN-main\DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\results\dn_ours `
  --models gpt-4o
```

## Generate And Score Baselines In One Run

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\run_generation_context_ablation.py `
  --config C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\configs\paper_baseline_config.json `
  --scale standard `
  --seed 42 `
  --theme-ids 1,2,3,4,5,6,12,18,54,73 `
  --max-games 10 `
  --max-eval-segments 5 `
  --run-name paper_baselines_10themes_5segments_scored `
  --judge-models gpt-4o
```

The final workbook is:

```text
C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\generation_context_ablation\outputs\runs\paper_baselines_10themes_5segments_scored\generation_context_ablation_results.xlsx
```

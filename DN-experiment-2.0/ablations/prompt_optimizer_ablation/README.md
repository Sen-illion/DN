# Prompt Optimizer Ablation

This directory contains a dedicated ablation workflow for measuring how the scene-image prompt optimizer affects image consistency.

Scope:
- only the prompt optimizer switch is ablated
- no evaluator ablation
- no generation-context ablation
- no protagonist reference-count ablation

Default root:
- `C:/Users/User/Desktop/DN-main/DN-experiment-2.0/ablations/prompt_optimizer_ablation`

## What is implemented

- dataset builder based on `game_themes_100.json`
- paired `prompt_optimizer_off` / `prompt_optimizer_on` task manifest
- actual optimizer on/off switch wired into `src/image/api_providers.py`
- generation runner that records raw prompt and final image prompt
- optional reuse of existing `theme_*` source folders to avoid regenerating text-only source data
- automatic scoring by reusing the existing multi-view image consistency script logic
- Excel workbook with these sheets:
  - `dataset_manifest`
  - `generation_runs`
  - `prompt_trace`
  - `per_sample_results`
  - `group_summary`
  - `group_comparison`
  - `failure_cases`
  - `config_snapshot`

## Group definition

- `prompt_optimizer_off`
  - disables `optimize_image_prompt_with_llm`
  - image prompt falls back to a minimal base prompt built directly from the scene text plus style / continuity hints
- `prompt_optimizer_on`
  - keeps the existing `optimize_image_prompt_with_llm` path
  - behavior stays as close as possible to current default logic

## Dataset build

Generate a fresh text-only source dataset and paired manifest:

```powershell
C:/Users/User/Desktop/DN-main/.venv/Scripts/python.exe `
  DN-experiment-2.0/ablations/prompt_optimizer_ablation/scripts/build_prompt_optimizer_dataset.py `
  --config DN-experiment-2.0/ablations/prompt_optimizer_ablation/config/default_config.json `
  --scale pilot
```

Reuse existing `DN-experiment-2.0/theme_*` folders instead of regenerating text-only source data:

```powershell
C:/Users/User/Desktop/DN-main/.venv/Scripts/python.exe `
  DN-experiment-2.0/ablations/prompt_optimizer_ablation/scripts/build_prompt_optimizer_dataset.py `
  --scale pilot `
  --source-root DN-experiment-2.0
```

Outputs:
- `results/datasets/<dataset_id>/dataset_manifest.json`
- `results/datasets/<dataset_id>/dataset_manifest.jsonl`
- `results/datasets/<dataset_id>/dataset_manifest.xlsx`
- `results/datasets/<dataset_id>/dataset_summary.json`

## Run the ablation

End-to-end run with dataset build + generation + scoring:

```powershell
C:/Users/User/Desktop/DN-main/.venv/Scripts/python.exe `
  DN-experiment-2.0/ablations/prompt_optimizer_ablation/scripts/run_prompt_optimizer_ablation.py `
  --build-dataset `
  --scale pilot
```

Run from an existing manifest:

```powershell
C:/Users/User/Desktop/DN-main/.venv/Scripts/python.exe `
  DN-experiment-2.0/ablations/prompt_optimizer_ablation/scripts/run_prompt_optimizer_ablation.py `
  --dataset-manifest C:/Users/User/Desktop/DN-main/DN-experiment-2.0/ablations/prompt_optimizer_ablation/results/datasets/<dataset_id>/dataset_manifest.json
```

Dry-run scoring only:

```powershell
C:/Users/User/Desktop/DN-main/.venv/Scripts/python.exe `
  DN-experiment-2.0/ablations/prompt_optimizer_ablation/scripts/run_prompt_optimizer_ablation.py `
  --dataset-manifest <manifest_json> `
  --dry-run-scoring
```

## Output layout

Per run:
- `results/runs/<run_id>/generated/prompt_optimizer_off/...`
- `results/runs/<run_id>/generated/prompt_optimizer_on/...`
- `results/runs/<run_id>/artifacts/prompt_optimizer_ablation_results.xlsx`
- `results/runs/<run_id>/artifacts/*.json`
- `results/runs/<run_id>/artifacts/*.jsonl`

## Notes

- The builder supports `pilot` / `standard` / `full`, fixed random seed, and paired on/off manifest rows.
- The runner records whether the optimizer was enabled, the raw prompt basis, the final prompt sent to image generation, generation success, timing, and scoring outputs.
- When judge model credentials are not available, scoring falls back to a dry-run table so the workbook structure still gets generated.

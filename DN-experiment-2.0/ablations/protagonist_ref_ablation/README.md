# Protagonist Reference Ablation

This experiment isolates one variable only: how many protagonist reference images are actually passed into scene image generation.

## What this ablation compares

Three groups are supported:

1. `protagonist_ref_0`
   - Pass `0` protagonist references.
2. `protagonist_ref_1`
   - Pass `1` protagonist reference.
   - Default interpretation: front view only.
3. `protagonist_ref_3`
   - Pass `3` protagonist references.
   - Default interpretation: front / side / back.

## Naming compatibility

The existing pipeline still writes protagonist views as:

- `main_character.png`
- `main_character_side.png`
- `main_character_back.png`

To avoid breaking existing logic, the ablation code also tolerates small naming variants when resolving references, in this order:

- metadata-defined filenames from `metadata.json`
- front: `main_character.png`, `main_character_front.png`, `front.png`
- side: `main_character_side.png`, `main_character_side_view.png`, `side.png`
- back: `main_character_back.png`, `main_character_back_view.png`, `back.png`

## Directory layout

All new code and outputs live under:

`C:\Users\User\Desktop\DN-main\DN-experiment-2.0\ablations\protagonist_ref_ablation`

Important subdirectories:

- `configs/`
- `scripts/`
- `datasets/`
- `results/`

## Files added here

- `configs/protagonist_ref_ablation_config.json`
- `scripts/shared.py`
- `scripts/build_protagonist_ref_ablation_dataset.py`
- `scripts/run_protagonist_ref_ablation.py`
- `README.md`

## Dataset builder

The dataset builder does two things:

1. samples themes from `game_themes_100.json` with a fixed seed
2. materializes a text-only source dataset so all three groups reuse the same themes, game structure, and segment text

Each dataset row includes at least:

- `theme_id`
- `theme`
- `base_game_id`
- `segment_index`
- `protagonist_ref_group`
- `expected_protagonist_ref_count`
- `actual_protagonist_ref_count` (blank at planning time, filled by runner output)
- `actual_protagonist_ref_paths` (empty at planning time, filled by runner output)

## Dataset variants

The builder now supports isolated variants:

- `general` keeps the existing behavior and continues to write latest pointers under `datasets/`.
- `hard_identity` writes under `datasets/hard_identity/`, uses dataset ids like `protagonist_ref_hard_identity_dataset_<timestamp>`, and adds explicit prompt-level identity stress constraints before image generation.

Hard-identity rows include auditable metadata:

- `dataset_variant`
- `difficulty_tags`
- `hard_score`
- `view_bucket`
- `protagonist_visible_required`
- `prompt_hardening_profile`

The hard score is rule-based: side/back view `+2`, face occlusion `+2`, long shot `+1`, extreme lighting `+1`, action-heavy pose `+1`, and continuity-sensitive details `+1`. Every hard-identity sample is generated with `protagonist_visible_required=true` and `hard_score>=2`.

Example hard-identity build:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\build_protagonist_ref_ablation_dataset.py `
  --dataset-variant hard_identity `
  --size pilot
```

### Example build commands

Pilot:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\build_protagonist_ref_ablation_dataset.py `
  --size pilot
```

Standard:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\build_protagonist_ref_ablation_dataset.py `
  --size standard
```

Full:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\build_protagonist_ref_ablation_dataset.py `
  --size full
```

## Runner

The runner reuses the same text-only dataset for all groups and then:

1. generates protagonist references for the run game id
2. forces the scene image pipeline to pass exactly `0`, `1`, or `3` protagonist references
3. records how many protagonist references were actually passed
4. exports per-group manifests in `theme_*` layout
5. reuses the existing legacy image-consistency scorer and aggregator
6. writes a comparison workbook

### Example run commands

Run all three groups and score them:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\run_protagonist_ref_ablation.py `
  --dataset-manifest DN-experiment-2.0\ablations\protagonist_ref_ablation\datasets\latest_dataset_manifest.jsonl
```

Run the isolated hard-identity dataset:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\run_protagonist_ref_ablation.py `
  --dataset-manifest DN-experiment-2.0\ablations\protagonist_ref_ablation\datasets\hard_identity\latest_hard_identity_dataset_manifest.jsonl
```

Run a smoke-sized pass without scoring:

```powershell
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\ablations\protagonist_ref_ablation\scripts\run_protagonist_ref_ablation.py `
  --dataset-manifest DN-experiment-2.0\ablations\protagonist_ref_ablation\datasets\latest_dataset_manifest.jsonl `
  --skip-scoring `
  --smoke-segments 1 `
  --max-samples 1
```

## Result workbook

The main workbook is written to each run under:

`...\results\<run_id>\analysis\protagonist_ref_ablation_results.xlsx`

It contains these sheets:

- `dataset_manifest`
- `generation_runs`
- `protagonist_reference_usage`
- `per_sample_results`
- `group_summary`
- `group_comparison`
- `dataset_variant_summary`
- `view_bucket_summary`
- `failure_cases`
- `config_snapshot`

## Metrics included

At minimum, the runner exports:

- `overall_score_mean`
- per-dimension means
- `reference_identity_fidelity_mean` proxy from `subject_attribute_consistency`
- `view_match_accuracy_mean` proxy from `spatial_consistency`
- side/back/mixed subset summaries via `view_bucket_summary`
- `valid_samples`
- `coverage`
- `success_generation_rate`
- `avg_actual_protagonist_ref_count`
- `avg_generation_duration_seconds`

## Legacy scripts reused

The runner intentionally reuses these existing scripts instead of reimplementing the scorer:

- `DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\scripts\score_image_consistency_per_game.py`
- `DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\scripts\aggregate_multiview_results.py`

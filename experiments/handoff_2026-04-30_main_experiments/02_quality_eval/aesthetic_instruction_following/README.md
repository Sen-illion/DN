# Aesthetic Consistency and Instruction Following Evaluation

This package evaluates visual quality for the formal20 experiment without regenerating images.
It uses the latest DN v15 pregen60 full-ready outputs and the existing StoryDiffusion, SDM-v2,
and IC-LoRA formal20 image outputs.

## Source-of-truth inputs

- Benchmark constraints: `experiments/benchmark/dn_quality_benchmark_v1.json`
- DN outputs: `experiments/benchmark/standard_runs/benchmark_v15_fullready_nextturn_pregen60s20_composite20_v1.json`
- Baseline outputs: `remote_baseline_results_20260430/outputs/*formal20*`

## Metrics

Instruction following is scored per image from 1 to 5:

- `theme_alignment`
- `text_image_alignment`
- `style_following`
- `constraint_coverage`
- `forbidden_violation`
- `instruction_following_score`

Aesthetic consistency is scored per `(system, benchmark_id)` group from 1 to 5:

- `style_lighting_consistency`
- `subject_attribute_consistency`
- `scene_world_consistency`
- `composition_quality`
- `artifact_rate`
- `aesthetic_consistency_score`

## Workflow

```powershell
python experiments\handoff_2026-04-30_main_experiments\02_quality_eval\aesthetic_instruction_following\scripts\build_quality_eval_manifest.py

# Validate the manifest without API calls.
python experiments\handoff_2026-04-30_main_experiments\02_quality_eval\aesthetic_instruction_following\scripts\run_vlm_quality_judge.py --validate-only

# Optional VLM scoring, requires OPENAI_API_KEY. Use --limit for smoke tests.
python experiments\handoff_2026-04-30_main_experiments\02_quality_eval\aesthetic_instruction_following\scripts\run_vlm_quality_judge.py --mode both --judge-model gpt-4.1 --limit 4

# Reproducible automatic fallback/proxy when VLM API access is unavailable.
python experiments\handoff_2026-04-30_main_experiments\02_quality_eval\aesthetic_instruction_following\scripts\run_clip_proxy_quality_eval.py

python experiments\handoff_2026-04-30_main_experiments\02_quality_eval\aesthetic_instruction_following\scripts\aggregate_quality_scores.py
```

## Generated artifacts

- `results/quality_eval_manifest_formal20_v1.jsonl`: 240 image-level records, covering 4 systems x 20 benchmark items x 3 turn/image types.
- `results/quality_eval_groups_formal20_v1.json`: 80 `(system, benchmark_id)` groups for cross-turn aesthetic consistency scoring.
- `results/missing_or_invalid_images.csv`: image/result integrity report.
- `results/manifest_coverage_summary.json`: coverage summary for reproducibility checks.
- `results/human_rating_template_formal20_v1.csv`: fallback manual scoring workbook.
- `results/per_image_instruction_following_scores.jsonl`: VLM or human-transcribed per-image instruction scores.
- `results/per_group_aesthetic_consistency_scores.jsonl`: VLM or human-transcribed group consistency scores.
- `results/clip_proxy_quality_details.jsonl`: CLIP/CV proxy diagnostics for each image.
- `results/quality_summary_by_system.csv`: paper-facing summary table generated from real score files.
- `results/quality_summary_by_dimension.csv`: dimension-level diagnostic table.
- `results/quality_failure_cases.md`: low-score case list for error analysis.

Note: some auxiliary Chinese fields in the benchmark JSON snapshot contain encoding damage. The manifest repairs the main `theme` field from the v15 formal20 summary table when possible, but some long scene texts and constraints may still be partially corrupted. Judge prompts explicitly instruct the evaluator to rely on readable theme/style/prompt evidence when this happens.

## Current status

- Manifest generation is main-ready and uses formal20 only.
- Strict image validation finds 239 valid image records and 1 invalid zero-byte SDM-v2 first-turn image (`DNQBV1_004`).
- Judge scoring is implemented but intentionally not run automatically, because it may incur API cost.
- CLIP+CV proxy scoring has been run. It is a real automatic measurement, but it should be treated as a proxy and confirmed by VLM or human judging before final paper submission.
- If judge API is unavailable, use `results/human_rating_template_formal20_v1.csv` for manual scoring.

## Current automatic proxy summary

| System | N images | N groups | Instruction Following | Aesthetic Consistency | Theme Violation Rate |
|---|---:|---:|---:|---:|---:|
| DN | 60 | 20 | 4.386 | 4.619 | 0.033 |
| StoryDiffusion | 60 | 20 | 3.620 | 4.485 | 0.017 |
| SDM-v2 | 59 | 20 | 3.008 | 4.764 | 0.136 |
| IC-LoRA | 60 | 20 | 2.351 | 4.403 | 0.467 |

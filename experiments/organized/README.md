# DN Organized Experiment Data

Generated: 2026-05-01T12:19:02

This directory reorganizes currently usable DN experiment artifacts into two searchable parts: main experiments and ablation experiments.
Original source files were not deleted or moved; selected useful files were copied here with source manifests.

## Main Experiments

| Folder | Purpose | Status |
| --- | --- | --- |
| `main_experiments/01_dn_vs_image_baselines` | DN vs Image Baselines | usable, see README |
| `main_experiments/02_efficiency_benchmark` | Efficiency Benchmark | usable, see README |
| `main_experiments/03_text_quality_and_planning` | Text Quality And Planning | usable, see README |
| `main_experiments/04_visual_consistency` | Visual Consistency | usable, see README |
| `main_experiments/05_human_eval_optional` | Human Evaluation Optional | usable, see README |

## Ablation Experiments

| Folder | Purpose | Status |
| --- | --- | --- |
| `ablations/01_council_ablation` | Council Ablation | usable, see README |
| `ablations/02_pregeneration_ablation` | Pregeneration Ablation | usable, see README |
| `ablations/03_text_ablation` | Text Ablation | usable, see README |
| `ablations/04_generation_context_ablation` | Generation Context Ablation | usable, see README |
| `ablations/05_protagonist_reference_ablation` | Protagonist Reference Ablation | usable, see README |
| `ablations/06_readwait_ablation` | Read Wait Ablation | partial |

## Quick Takeaways

- Latest image baseline comparison: DN beats SDM-v2 and StoryDiffusion under GPT-4o visual evaluation; IC-LoRA is not yet a successful image baseline in the latest run.
- Efficiency: no_council is faster for worldview-only repeated tests, but full-chain default is safer as the main result.
- Text: DN beats DOC baseline and ties Rolling in the currently organized comparisons.
- Visual consistency: multi-judge scores are around 4/5; DreamSim remains unfinished.
- Human evaluation: templates/checks exist, but formal human-eval data is not ready.

## Navigation Files

- `DATA_INDEX.csv`: searchable index of copied files and relevant source/candidate files.
- `CLEANUP_CANDIDATES.md`: review-only cleanup proposal; no files were deleted.
- Per-experiment `source_manifest.json`: trace copied files back to original paths.


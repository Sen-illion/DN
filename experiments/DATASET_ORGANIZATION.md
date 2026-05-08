# Useful Dataset Organization

Generated from the current `experiments/` workspace.

## What Counts As Useful

Useful datasets are files that can support the paper tables, plots, or reproducible experiment comparisons:

- Keep: curated manifests, benchmark CSV/JSON/XLSX, ablation result workbooks, baseline comparison outputs, visual/text consistency evaluation data, human-eval templates.
- Deprioritize: `_archive_or_cleanup_candidates/`, `node_modules/`, `__pycache__/`, `vendor_py/`, temporary spreadsheet lock files, raw dependency caches.
- Raw data is still useful when it is the only source of images/text samples; duplicated archived copies should not be the first source.

## Left/Right Working Views

| Side | Use | Primary location | Logic |
| --- | --- | --- | --- |
| Left table | Paper-facing curated view | `experiments/organized/` | Best place to read and cite. It groups useful artifacts by paper experiment: main experiments first, ablations second. |
| Right table | Source/current working view | `experiments/paper_modules/`, `experiments/benchmark/`, `experiments/text_ablation/`, `experiments/baseline_integration/`, `experiments/baselines/` | Use when tracing provenance, rerunning, or checking raw/current outputs. |

## Useful Dataset Inventory

| Dataset / module | Paper role | Best curated position | Source/current position | Main files | Status |
| --- | --- | --- | --- | --- | --- |
| DN vs image baselines | Main experiment, image generation baseline comparison | `experiments/organized/main_experiments/01_dn_vs_image_baselines/` | `experiments/paper_method_view/`, `experiments/baselines/` | `summary/*.csv`, `summary/*.json`, reports | Usable |
| Efficiency benchmark | Main experiment, runtime/throughput/effectiveness | `experiments/organized/main_experiments/02_efficiency_benchmark/` | `experiments/benchmark/outputs/`, `experiments/benchmark/standard_runs/`, `experiments/paper_modules/1_main_experiments/current_internal_summaries/` | `benchmark_v1_standard_run_summary.xlsx`, `dn_efficiency_effectiveness_summary_v1.xlsx`, `dn_current_best_conclusions_v2.xlsx` | Usable |
| Text quality and planning | Main experiment, DN vs DOC/Rolling/coherence | `experiments/organized/main_experiments/03_text_quality_and_planning/` | `experiments/paper_modules/2_supplementary_validation/text_coherence/`, `experiments/baselines/text_rolling_4o/` | `coherence_*.xlsx`, `coherence_comparison_gpt4o.xlsx`, `rolling_vs_dn_5_summary.xlsx` | Usable |
| Visual consistency | Main/supplementary visual consistency evaluation | `experiments/organized/main_experiments/04_visual_consistency/` | `experiments/paper_modules/2_supplementary_validation/image_consistency/` | `rusults_game_image_consistency.xlsx`, `pairs.csv`, `per_game_ensemble_mean.csv`, `comparison_summary.json` | Usable |
| Human evaluation templates | Optional human rating worksheets | `experiments/organized/main_experiments/05_human_eval_optional/` | `experiments/benchmark/outputs/` and organized workbooks | `dn_human_rating_template_v1.xlsx`, `human_image_consistency_rating_v1_grouped.xlsx`, `human_text_consistency_rating_v1.xlsx` | Template-ready; formal human data not complete |
| Council ablation | Ablation: with/without council | `experiments/organized/ablations/01_council_ablation/` | `experiments/paper_modules/3_ablations/council_ablation/`, `experiments/paper_method_view/4_ablations/council/` | `benchmark_v1_*_default_20.json`, `benchmark_v1_*_no_council_20.json`, summary CSV/JSON | Usable |
| Pregeneration ablation | Ablation: pregeneration on/off | `experiments/organized/ablations/02_pregeneration_ablation/` | `experiments/paper_modules/3_ablations/pregeneration_ablation/`, `experiments/paper_method_view/4_ablations/pregeneration/` | `benchmark_v3_pregen_clean_ablation_table.csv`, `benchmark_v3_fullchain_pregen_*_clean12.json` | Usable |
| Text ablation | Ablation: worldview/text switch combinations | `experiments/organized/ablations/03_text_ablation/` | `experiments/text_ablation/` | `results/coherence_comparison_cleaned.xlsx`, `results/coherence_wv_*.xlsx`, `data/wv_*/*/*.json`, `data/wv_*/*/*.png` | Usable; raw images are large |
| Generation context ablation | Ablation: naive T2I vs prompt memory vs previous image vs visual bible | `experiments/organized/ablations/04_generation_context_ablation/` | `DN-experiment-2.0/ablations/generation_context_ablation/outputs/` copied into organized workbooks | `dataset_manifest.xlsx`, `dataset_manifest.*.xlsx`, `paper_baseline_comparison.xlsx`, `group_comparison_summary.*` | Usable |
| Protagonist reference ablation | Ablation: protagonist reference / identity consistency | `experiments/organized/ablations/05_protagonist_reference_ablation/` | `DN-experiment-2.0/ablations/protagonist_reference_ablation/outputs/` copied into organized workbooks | `latest_hard_identity_dataset_manifest.xlsx`, `latest_hard_identity_results.xlsx`, `latest_results.xlsx` | Usable |
| Read-wait ablation | Ablation: read-wait/pregeneration timing | `experiments/organized/ablations/06_readwait_ablation/` | `experiments/paper_modules/3_ablations/readwait_ablation/`, `experiments/benchmark/standard_runs/` | `benchmark_v4_readwait_off_0s_6.json`, `benchmark_v9_readwait_60s_merged_12v12_workbook.xlsx` | Partial |
| Baseline integration normalized runs | Unified baseline schema for paper tables | `experiments/baseline_integration/normalized_runs/` | same | `doc_yunwu/*/item_*.json`, `genagents_*.normalized.json` | Useful for table normalization |
| DOC / Rolling text baselines | Text baseline source outputs | `experiments/baselines/doc_baseline/`, `experiments/baselines/text_rolling_4o/` | same | `run_doc_on_dn.py`, `coherence_rolling_5.xlsx`, `rolling_vs_dn_5_summary.xlsx`, `theme_*/*` | Usable |

## Spreadsheet Cell Positions

Most workbooks are single contiguous tables starting at `A1`. The important positions are:

| Workbook | Sheet | Left/table position | Right/table position | Notes |
| --- | --- | --- | --- | --- |
| `experiments/text_ablation/results/coherence_comparison_cleaned.xlsx` | `Summary` | `A6:G10` | `I2` note cell | Only workbook detected with a visible left block plus a right-side note column. Main ranked table is left. |
| `experiments/text_ablation/results/coherence_comparison_cleaned.xlsx` | `FairCompare` | `A1:G9` | none | Fair four-way comparison table. |
| `experiments/text_ablation/results/coherence_comparison_cleaned.xlsx` | `ExcludedSamples` | `A1:G18` | none | Excluded fallback-like samples. |
| `experiments/benchmark/outputs/benchmark_v1_standard_run_summary.xlsx` | `Overview` | `A1:D14` | none | Summary metadata. |
| `experiments/benchmark/outputs/benchmark_v1_standard_run_summary.xlsx` | `WorldviewAB20` | `A1:J21` | none | Worldview 20-run comparison. |
| `experiments/benchmark/outputs/benchmark_v1_standard_run_summary.xlsx` | `FullChain20` | `A1:L21` | none | Full-chain 20-run comparison. |
| `experiments/benchmark/outputs/dn_efficiency_effectiveness_summary_v1.xlsx` | `Benchmark20` | `A1:I21` | none | Benchmark table. |
| `experiments/benchmark/outputs/dn_efficiency_effectiveness_summary_v1.xlsx` | `FullChainProxy12` | `A1:T13` | none | Wide proxy table. |
| `experiments/organized/ablations/04_generation_context_ablation/workbooks/dataset_manifest.xlsx` | `dataset_manifest` | `A1:Q37` | none | Dataset manifest for generation-context ablation. |
| `experiments/organized/ablations/05_protagonist_reference_ablation/workbooks/latest_hard_identity_results.xlsx` | `per_sample_results` | `A1:AU46` | none | Widest protagonist-reference result table. |
| `experiments/organized/main_experiments/04_visual_consistency/workbooks/rusults_game_image_consistency.xlsx` | `per_image_scores` | `A1:O232` | none | Per-image evaluator scores. |
| `experiments/organized/main_experiments/04_visual_consistency/workbooks/rusults_game_image_consistency.xlsx` | `per_game_summary` | `A1:J31` | none | Per-game summary. |
| `experiments/organized/main_experiments/05_human_eval_optional/workbooks/human_image_consistency_rating_v1_grouped.xlsx` | `待评图片样本` | `A1:R51` | none | Image sample table. |
| `experiments/organized/main_experiments/05_human_eval_optional/workbooks/human_image_consistency_rating_v1_grouped.xlsx` | `图片评分表` | `A1:AB51` | none | Human image rating table. |
| `experiments/organized/main_experiments/05_human_eval_optional/workbooks/human_text_consistency_rating_v1.xlsx` | `待评文本样本` | `A1:K11` | none | Text sample table. |
| `experiments/organized/main_experiments/05_human_eval_optional/workbooks/human_text_consistency_rating_v1.xlsx` | `文本评分表` | `A1:R11` | none | Human text rating table. |

## Current Layout Logic

The current useful data is arranged in two overlapping ways:

1. `experiments/organized/` is the clean paper-facing index.
   - `main_experiments/` contains the primary paper claims.
   - `ablations/` contains mechanism/ablation support.
   - Each subfolder keeps `summary/`, `workbooks/`, `reports/`, and `source_manifest.json` when available.

2. `experiments/paper_modules/` is a paper-module working view.
   - `1_main_experiments/`: current internal summaries for main claims.
   - `2_supplementary_validation/`: text/image consistency and repeatability checks.
   - `3_ablations/`: council, pregeneration, read-wait ablations.

3. Original/current source directories remain in place.
   - `benchmark/`: efficiency and runtime source outputs.
   - `text_ablation/`: raw text-ablation JSON/PNG datasets plus cleaned result workbooks.
   - `baseline_integration/`: normalized baseline outputs for comparison tables.
   - `baselines/`: baseline scripts and outputs.

4. The recommended reading order is:
   - Start at `experiments/organized/README.md`.
   - Use `experiments/organized/DATA_INDEX.csv` for source tracing.
   - Use `experiments/paper_modules/` only when matching paper section structure.
   - Avoid `_archive_or_cleanup_candidates/` unless recovering old duplicated artifacts.

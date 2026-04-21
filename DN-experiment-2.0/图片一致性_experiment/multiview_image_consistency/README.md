# DN Experiment 2.0: Multi-View Image Consistency

This package applies the `dn-experiment-pack` workflow to image consistency checks.
It is designed to be reusable across future DN batches.

## 1) Experiment question

Can we reliably score image consistency from multiple angles, and do judge models agree on those scores?

## 2) What changes vs what stays fixed

- Changed (independent variable): judge model and/or prompt variant.
- Fixed controls:
  - same image set
  - same scoring schema
  - same score range (`1` to `5`)
  - same aggregation formula

## 3) Metrics

- `dimension_score_mean`: per-dimension average score (`1-5`)
- `overall_score_mean`: weighted mean over all dimensions
- `judge_disagreement_mean`: average per-sample standard deviation across judge models
- `coverage`: usable image samples / discovered samples

## 4) Reusable artifacts in this folder

- `configs/experiment_config.example.json`: experiment design and thresholds
- `prompts/system_prompt_multiview.txt`: rubric and strict JSON output rules
- `prompts/user_prompt_template.txt`: single-sample prompt input template
- `schemas/multiview_judgement.schema.json`: standard output schema for judges
- `scripts/build_eval_manifest.py`: build image sample manifest from `*_image_paths.json`
- `scripts/aggregate_multiview_results.py`: aggregate JSONL judge outputs into report files
- `results/`: generated manifests, summaries, and report markdown

## 5) Suggested workflow (chosen route)

This experiment uses a mixed route from `dn-experiment-pack`:

1. CLI route: build and aggregate repeatable runs.
2. Notebook route (optional): deeper analysis/plots after aggregation.
3. Screenshot route (optional): save positive/negative examples for manual review packets.

## 6) Quick start

From repo root:

```powershell
# 1) Build manifest from current DN-experiment-2.0 image path files
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\experiments\multiview_image_consistency\scripts\build_eval_manifest.py `
  --experiment-root DN-experiment-2.0 `
  --output-dir DN-experiment-2.0\experiments\multiview_image_consistency\results

# 2) Run judge models externally (or with your own runner) and write JSONL
#    format compatible with schemas/multiview_judgement.schema.json

# 3) Aggregate judge JSONL into final summary + conclusion
C:\Users\User\Desktop\DN-main\.venv2\Scripts\python.exe `
  DN-experiment-2.0\experiments\multiview_image_consistency\scripts\aggregate_multiview_results.py `
  --input-jsonl DN-experiment-2.0\experiments\multiview_image_consistency\results\latest_judgements.jsonl `
  --config DN-experiment-2.0\experiments\multiview_image_consistency\configs\experiment_config.example.json `
  --output-dir DN-experiment-2.0\experiments\multiview_image_consistency\results
```

## 7) Current strongest takeaway (2026-04-18)

- A scan of existing `DN-experiment-2.0` image manifests shows low usable image coverage.
- Result: run data refresh first, then judge-model comparison, otherwise conclusions will be unstable.

## 8) Biggest uncertainty

- Whether low coverage is temporary (incomplete generation) or systematic (pipeline failure in some themes).

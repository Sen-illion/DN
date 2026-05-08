# DN vs Image Baselines

- Type: main
- Question: DN generated images compared with image baselines generated from DN text prompts.
- Strongest takeaway: Latest usable comparison shows DN > SDM-v2 and DN > StoryDiffusion by GPT-4o visual judging; IC-LoRA is manifest-only in the latest run.
- Main uncertainty: IC-LoRA and skipped rows need completion before this becomes a fully balanced baseline table.

## Key Metrics

- Coverage: SDM-v2 100/100, StoryDiffusion 100/100, IC-LoRA 0 successful images / 100 indexed rows.
- Eval pairs: 77 each for SDM-v2 and StoryDiffusion.
- Average scores: DN 4.7095 vs SDM-v2 2.4442; DN 4.7015 vs StoryDiffusion 3.6288.
- Skipped rows: 146, mainly missing DN reference images or manifest-only baseline outputs.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 15 copied files and original locations.

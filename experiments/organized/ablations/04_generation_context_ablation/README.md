# Generation Context Ablation

- Type: ablation
- Question: Effect of different image generation context variants.
- Strongest takeaway: dn_ours is best, prompt_plus_prev_image is close, naive_t2i is clearly weaker.
- Main uncertainty: Some groups have missing samples; compare means with coverage in mind.

## Key Metrics

- dn_ours: 9/9 scored, overall 9.2222.
- prompt_plus_prev_image: 7/9 scored, overall 9.1429.
- prompt_only_memory: 9/9 scored, overall 9.0.
- visual_bible: 9/9 scored, overall 9.0.
- naive_t2i: 7/9 scored, overall 7.0.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 8 copied files and original locations.

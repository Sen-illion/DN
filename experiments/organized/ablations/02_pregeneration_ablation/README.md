# Pregeneration Ablation

- Type: ablation
- Question: Effect of pregeneration on clean full-chain runs.
- Strongest takeaway: Clean v3 runs show pregen_on reduces worldview mean versus pregen_off, while option latency differences are tiny by median.
- Main uncertainty: pregen_off contains a 680s outlier; conclusions should emphasize robust medians and clean runs.

## Key Metrics

- Clean12 pregen_off: full_success 12/12, worldview mean 73.377s, median 9.634s.
- Clean12 pregen_on: full_success 12/12, worldview mean 16.566s, median 8.657s.
- Option median delta on-minus-off: 0.005s; not a meaningful option-stage latency win.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 7 copied files and original locations.

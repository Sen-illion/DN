# Text Quality And Planning

- Type: main
- Question: Story/text coherence and planning quality against text baselines.
- Strongest takeaway: DN beats DOC baseline on the 10-theme GPT-4o comparison and ties Rolling on the 5-theme comparison.
- Main uncertainty: Some older Chinese theme text is garbled in source files; final paper tables should use cleaned labels.

## Key Metrics

- DOC vs DN, n=10: DOC GPT-4o mean 4.2; DN mean 4.7; DOC-DN -0.5.
- Rolling vs DN, n=5: Rolling 4.8; DN 4.8; tie.
- Original text consistency workbook/log covers 10 games with Claude/Gemini/GPT-4o judging.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 16 copied files and original locations.

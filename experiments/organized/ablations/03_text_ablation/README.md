# Text Ablation

- Type: ablation
- Question: Contribution of worldview and text modules to story coherence.
- Strongest takeaway: Both modules on gives the best cleaned cross-condition average; turning both off is worst.
- Main uncertainty: Themes 12/18/54/73 were excluded because samples looked fallback-like; cleaned comparison is only six themes.

## Key Metrics

- wv_on_text_on: n=6, avg_consistency 4.6296.
- wv_off_text_on: n=6, avg_consistency 4.3889.
- wv_on_text_off: n=6, avg_consistency 4.3704.
- wv_off_text_off: n=6, avg_consistency 4.0556.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 6 copied files and original locations.

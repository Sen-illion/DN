# Protagonist Reference Ablation

- Type: ablation
- Question: Effect of 0, 1, or 3 protagonist reference images on identity and consistency.
- Strongest takeaway: Three references are slightly better on strict hard-identity subset, but ordinary set does not show a strong monotonic gain.
- Main uncertainty: Reference count and actual usable reference count diverge in some hard-identity runs; use curated strict for the cleanest comparison.

## Key Metrics

- Ordinary set: ref_0 overall 9.0667; ref_1 9.0; ref_3 9.0.
- Hard identity: ref_0 overall 8.8667; ref_1 8.8; ref_3 8.9333.
- Curated strict: ref_0 8.8; ref_1 8.8; ref_3 9.0.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 9 copied files and original locations.

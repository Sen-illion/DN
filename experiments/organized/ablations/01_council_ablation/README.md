# Council Ablation

- Type: ablation
- Question: Default configuration versus no_council for worldview and full-chain latency/reliability.
- Strongest takeaway: no_council is faster for worldview-only repeated runs, but full-chain default has better success reliability.
- Main uncertainty: Worldview-only and full-chain windows differ; provider variance remains a confounder.

## Key Metrics

- Full-chain default: 20/20 success; no_council: 19/20 success.
- Full-chain worldview pairwise: default faster 14, no_council faster 6.
- Worldview-only repeated result favors no_council in most pairs.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 10 copied files and original locations.

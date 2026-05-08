# Efficiency Benchmark

- Type: main
- Question: End-to-end and worldview latency, success rate, and reliability under standardized DN benchmark runs.
- Strongest takeaway: Worldview no_council is faster in repeated worldview-only tests; full-chain default remains more reliable as a main result.
- Main uncertainty: Provider queue variance affects long-tail latency; cost/resource accounting is still missing.

## Key Metrics

- Worldview default 20/20: mean 33.657s, median 23.664s, p95 68.872s.
- Worldview no_council 20/20: mean 20.031s, median 14.938s, p95 44.556s.
- Repeat combined 40: default mean 37.832s; no_council mean 20.244s.
- Full-chain default 20/20: worldview mean 12.458s, option mean 7.662s, main-character mean 55.912s.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 17 copied files and original locations.

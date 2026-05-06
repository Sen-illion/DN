# Visual Consistency

- Type: main
- Question: Image consistency across generated scenes and reference images.
- Strongest takeaway: Multi-judge visual scores cluster around 4/5; CLIP-I/DINOv2 pair metrics exist for 19 image pairs, but DreamSim is unfinished.
- Main uncertainty: Embedding metrics are partial and should be paired with renewed image coverage before final claims.

## Key Metrics

- Multi-view visual quality: 10 game IDs, three judge models, overall means roughly 3.93-4.13 / 5.
- Image-pair metric set: pair_count 19, CLIP-I mean 0.560501, DINOv2 mean 0.177302.
- DreamSim status: not completed because default checkpoint download timed out.

## Files

- `summary/`: machine-readable summaries, CSV/JSON/JSONL.
- `reports/`: markdown, text, or log reports.
- `workbooks/`: spreadsheet workbooks.
- `scripts/`: scripts copied only when they are directly needed to interpret a partial result.
- `source_manifest.json`: source-to-destination trace.

## Source Manifest

See `source_manifest.json` for 9 copied files and original locations.

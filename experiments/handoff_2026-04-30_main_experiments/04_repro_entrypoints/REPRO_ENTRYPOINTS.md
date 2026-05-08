# REPRO_ENTRYPOINTS

## Current baseline runners
- `D:/Projects/DN/scripts/baselines/run_storydiffusion.py`
- `D:/Projects/DN/scripts/baselines/run_sdmv2.py`
- `D:/Projects/DN/scripts/baselines/run_iclora.py`
- `D:/Projects/DN/scripts/baselines/run_doc.py`

## Current DN full-ready benchmark entrypoints
- `D:/Projects/DN/experiments/benchmark/pregen_read_wait_runner.py`
- `D:/Projects/DN/experiments/benchmark/build_fullready_nextturn_outputs.py`
- `D:/Projects/DN/experiments/benchmark/run_fullready_v14_windows.ps1`

## Current subset files
- `D:/Projects/DN/baselines/subsets/dn_style_smoke3.json`
- `D:/Projects/DN/baselines/subsets/dn_style_formal8.json`
- `D:/Projects/DN/baselines/subsets/dn_style_formal20.json`

## Current schemas and adapter docs
- `D:/Projects/DN/experiments/baseline_integration/schema/unified_baseline_run_schema.md`
- `D:/Projects/DN/experiments/baseline_integration/schema/playable_latency_run_schema.md`
- `D:/Projects/DN/experiments/baseline_integration/adapters/README.md`
- `D:/Projects/DN/experiments/baseline_integration/adapters/doc_adapter.md`
- `D:/Projects/DN/experiments/baseline_integration/adapters/storydiffusion_adapter.md`

## Remote environment documentation
- `D:/Projects/DN/docs/AUTODL_CLOUD_EXPERIMENT_ENV.md`
- current remote result root used for the image baseline batch: `/root/autodl-tmp/outputs`

## Recommended continuation order
1. use the current formal20 summaries and review sheets as the starting point
2. if continuing image experiments, reuse the existing baseline runners and formal20 subset
3. if continuing DOC comparison, reuse `run_doc.py` in fallback mode first, then only attempt upstream reproduction separately
4. if continuing DN text latency tables, start from the playable-latency scaffold under `experiments/paper_method_view`
5. if continuing the strict DN full-ready comparison, start from `run_fullready_v14_windows.ps1` or run `pregen_read_wait_runner.py` directly against the local DN web server

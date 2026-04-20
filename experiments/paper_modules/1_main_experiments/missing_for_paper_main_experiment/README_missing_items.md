# Missing Main-Experiment Artifacts

Still needed for a paper-ready main experiment section:

1. A unified baseline comparison table
   - Ours vs at least 2-3 external or internal baselines
   - same benchmark set, same sample size, same evaluation protocol

2. A quality comparison table
   - human rating and/or strong automatic quality metrics
   - should cover story quality, image quality, consistency, and overall preference if available

3. An end-to-end efficiency table
   - total latency
   - first meaningful result time / first interactive result time if this is part of the claim
   - success rate
   - long-tail stats such as p95

4. A cost/resource table
   - token cost, API cost, request count, or model-call count
   - optional if the paper does not claim efficiency-cost tradeoffs, but highly recommended

5. A baseline raw-run folder
   - raw json/csv summaries for each baseline run used in the final main table
   - helps trace every cell in the final paper table back to source runs

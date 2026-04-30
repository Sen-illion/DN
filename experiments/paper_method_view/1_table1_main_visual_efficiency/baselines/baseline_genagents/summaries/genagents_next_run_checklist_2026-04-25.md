# GenAgents Next Run Checklist

## Immediate command order
1. set `OPENAI_API_KEY`
2. run:
   - `protocol/run_genagents_consistency.py --output genagents_consistency_live.json`
3. summarize:
   - `protocol/summarize_genagents_runs.py --input genagents_consistency_live.json --output-json genagents_consistency_live_summary.json --output-csv genagents_consistency_live_per_item.csv`
4. export Table 2 row:
   - `protocol/export_genagents_table2_row.py`
5. merge into Table 2 scaffold:
   - `protocol/merge_genagents_into_table2_scaffold.py`
6. build eval packet:
   - `protocol/build_genagents_eval_packet.py --input genagents_consistency_live.json --output-csv genagents_eval_packet_live.csv --output-md genagents_eval_packet_live.md`

## What the live run should unlock
- non-zero `turn_success_rate`
- non-zero `item_full_success_rate`
- real per-turn latency
- first usable text-side external baseline row for the paper

## What still remains after the live run
- stronger consistency scoring
- optional human rating
- optional judge-model rubric instead of only heuristic placeholder metrics

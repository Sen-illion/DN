# Table 2 Alignment Note (2026-04-26)

## Goal
Reduce the comparison-gap between DN and GenAgents so the paper does not overclaim direct equivalence where the tasks are only partially matched.

## Current recommended aligned table
- `experiments/paper_method_view/2_table2_text_planning/summary_tables/text_baseline_comparison_aligned_2026-04-26_subset_v2.csv`

## Alignment strategy
- DN row is recomputed on the same 8 benchmark IDs used by `genagents_consistency_subset_v2`
- GenAgents row keeps its 8-item judged run results
- AIDungeon remains a deferred status row rather than an executable comparison row

## What is directly comparable
- sample coverage on the same 8 benchmark IDs
- run success / completion reliability
- latency mean and latency p95 as system-level execution signals
- text-side scenario grounding in a broad sense

## What is only partially comparable
- DN `worldview planning` vs GenAgents `persona-conditioned multi-turn response`
- both are text-side planning / consistency tasks, but they are not identical API outputs
- DN produces structured worldview artifacts; GenAgents produces conversational multi-turn reactions

## What should not be presented as directly comparable
- image quality
- text-image alignment
- branching option diversity
- DN worldview single-shot outputs vs GenAgents persona consistency scores as if they were the same metric

## Recommended wording for the paper
- use the aligned table as a `text-side baseline comparison`
- describe DN as a `structured worldview planning system`
- describe GenAgents as a `persona-consistent multi-turn text baseline`
- explicitly note that the comparison is task-aligned, not output-identical

## Practical recommendation
- for the main paper table, prefer the aligned CSV over the earlier broad scaffold
- keep the broader merged scaffold as archive evidence, but cite the aligned CSV in the results discussion

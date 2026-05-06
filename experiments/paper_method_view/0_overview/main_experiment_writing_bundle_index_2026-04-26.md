# 主实验写作产物索引（2026-04-26）

本文件用于固定当前主实验写作与结果材料的 source of truth。后续继续推进时，优先基于这里列出的文件更新，不再分散回溯旧草稿。

## 1. 核心结果表

- 唯一核心主表 source of truth：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\main_playable_latency_scaffold_2026-04-26.csv`
- WorldGeneration 补充表 source of truth：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\supplementary_playable_latency_worldgeneration_2026-04-26.csv`
- 历史候选表，仅作存档参考、不再作为正文引用源：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\main_playable_latency_with_light_2026-04-26.csv`

## 2. baseline 原始 summary

- DN：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\efficiency_metrics\benchmark_v1_summary_metrics.json`
- LIGHT：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_light\summaries\light_playable_latency_v2_en_summary_2026-04-26.json`
- Plan-Write-Revise：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_plan_write_revise\summaries\pwr_playable_latency_v1_summary_2026-04-26.json`
- GenAgents：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_genagents\summaries\genagents_playable_latency_summary_2026-04-26_subset_v2.json`
- WorldGeneration：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\baseline_worldgeneration\summaries\worldgeneration_playable_latency_v2_summary_2026-04-26.json`

## 3. 主实验协议与进度材料

- playable protocol：`C:\Users\zhang\Desktop\DN\experiments\baseline_integration\adapters\playable_protocol.py`
- subset v1：`C:\Users\zhang\Desktop\DN\experiments\baseline_integration\subsets\efficiency_playable_subset_v1.json`
- subset v2：`C:\Users\zhang\Desktop\DN\experiments\baseline_integration\subsets\efficiency_playable_subset_v2.json`
- 进度报告：`C:\Users\zhang\Desktop\DN\experiments\baseline_integration\reports\main_playable_latency_progress_2026-04-26.md`
- baseline 清单：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\baselines\main_playable_latency_checklist_2026-04-26.md`

## 4. 当前写作主稿

- 实验章节总稿：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\0_overview\experiment_section_draft_zh_2026-04-26.md`
- 主实验结果解释：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\0_overview\main_playable_latency_results_interpretation_zh_2026-04-26.md`
- 主实验段落候选：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\0_overview\main_playable_latency_results_paragraphs_zh_2026-04-26.md`
- 局限性与有效性威胁：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\0_overview\limitations_zh_2026-04-26.md`
- 图表 caption 包：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\0_overview\figure_table_caption_pack_zh_2026-04-26.md`
- Table 1 caption：`C:\Users\zhang\Desktop\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\table1_main_playable_latency_caption_zh_2026-04-26.md`

## 5. 当前冻结的主表成员与角色

- `DN`：完整系统主行
- `LIGHT`：优先权威 external baseline
- `Plan-Write-Revise`：速度参考 baseline
- `GenAgents`：状态连续性补充 baseline
- `WorldGeneration`：补充表，不进核心主表

## 6. 当前必须保持一致的关键口径

- 这是统一 playable-latency protocol 下的外部系统形态对比，不是完全同构竞赛。
- `DN` 行当前使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy。
- `LIGHT` 是核心主表中的优先权威 external row。
- `WorldGeneration` 仅保留为 supplementary fallback row。

## 7. 后续更新规则

- 若更新主实验数字，优先更新 summary JSON 与核心主表 CSV，再回写章节草稿。
- 若调整 baseline 角色，必须同时更新主表说明、Table 1 caption、baseline README / status 与局限性部分。
- 若引入新的外部 baseline，只有在具备 `source_links + protocol + raw_runs + summaries + status` 五类证据后，才允许进入主表讨论。
- 若只是补语言表达，不要改动主表成员定义与当前角色划分。
- 若引用 Table 1，一律指向 `main_playable_latency_scaffold_2026-04-26.csv`，不要再引用历史候选表。

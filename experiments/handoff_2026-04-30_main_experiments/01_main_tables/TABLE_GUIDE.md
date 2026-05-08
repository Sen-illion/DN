# Table Guide

## A. 严格主实验表

### `strict_fullready_main_comparison_2026-05-01.csv`
- 回答的问题：玩家点击后，到下一轮内容真正可交付为止，要等多久
- 当前成员：`DN`、`StoryDiffusion`、`SDM-v2`、`IC-LoRA`
- 角色定位：当前最严格、最应该优先引用的主实验表
- 状态：formal / main result

补充说明：

- `DN` 行使用 `normal20` full-ready next-turn 结果
- `StoryDiffusion / SDM-v2 / IC-LoRA` 行继续使用现有 formal20 next-turn continuation image 结果
- 这张表不再混入 `LIGHT / PWR / GenAgents`

## B. DN full-ready next-turn 明细表

### `benchmark_v14_fullready_nextturn_20_summary.json`
- 回答的问题：DN 在 `normal20` 和 `pregen60s20` 两套设置下，文本 ready、图像 ready、full-ready 各是多少
- 角色定位：DN 新主实验的 source-of-truth 汇总
- 状态：formal / main result

### `benchmark_v14_fullready_nextturn_20_table.csv`
- 回答的问题：20 条样本逐条的 full-ready next-turn 记录是什么
- 角色定位：逐样本追溯、误差分析、复核用明细表
- 状态：formal / supporting evidence

### `benchmark_v14_fullready_nextturn_normal20.json`
- 回答的问题：DN 在不吃预生成收益时，第二轮点击后的 full-ready latency 是多少
- 角色定位：严格主表中的 DN 数据源
- 状态：formal / main result

### `benchmark_v14_fullready_nextturn_pregen60s20.json`
- 回答的问题：DN 在 `read_wait_s = 60` 的预生成模拟下，full-ready latency 是多少
- 角色定位：机制收益证明，不直接替代 strict main table
- 状态：formal / mechanism result

## C. 图像 baseline 正式 formal20 表

### `first_turn_formal20_summary.csv`
- 回答的问题：首图生成有多快，成功率如何
- 样本量：20 / baseline
- 角色定位：图像 baseline 首图正式表
- 状态：formal / main result

### `next_turn_formal20_latency_summary.csv`
- 回答的问题：点击后生成下一张 continuation image 要多久
- 样本量：20 / baseline
- 角色定位：图像 baseline next-turn 正式表
- 状态：formal / main result

## D. 历史图像过程表

### `image_baseline_summary_20260430.csv`
- 回答的问题：smoke3 / formal8 / blocker / fallback 的历史推进过程
- 角色定位：排障与历程证据
- 状态：historical only

### `storydiffusion_expanded_summary_20260430.csv`
- 回答的问题：StoryDiffusion 从早期扩样到 formal20 稳定前经历了什么
- 角色定位：历程和稳定性补充
- 状态：historical only

## E. 历史文本参考表

### `main_playable_latency_scaffold_2026-04-26.csv`
- 回答的问题：文本 playable response 多快
- 成员：`DN`、`LIGHT`、`PWR`、`GenAgents`
- 角色定位：历史文本 playable-latency 参考组
- 状态：historical reference

### `supplementary_playable_latency_worldgeneration_2026-04-26.csv`
- 回答的问题：WorldGeneration 补充行如何放入同一历史文本协议
- 角色定位：补充参考
- 状态：historical reference

## F. DN 内部 benchmark 汇总

### `benchmark_v1_summary_metrics.csv` / `.json`
- 回答的问题：DN 自己内部各阶段 latency 和成功率是什么
- 角色定位：DN 内部 source-of-truth

### `dn_efficiency_effectiveness_summary_v1.xlsx`
- 回答的问题：如何用更适合阅读的工作簿看 DN 内部指标
- 角色定位：presentation / spreadsheet review

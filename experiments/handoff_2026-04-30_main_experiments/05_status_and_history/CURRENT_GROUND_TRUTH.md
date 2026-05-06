# Current Ground Truth

## 1. 当前最严格的主实验口径

当前最应该优先引用的主实验，不再是“文本 playable-latency 混合表”，而是下面这条更严格的口径：

- 玩家点击后，到该轮内容可交付为止
- 对 DN 来说，交付物定义为：`文本 continuation + 对应剧情图都 ready`
- 对图像 baseline 来说，交付物定义为：`next-turn continuation image ready`

对应主表：

- `D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\01_main_tables\strict_fullready_main_comparison_2026-05-01.csv`

这个主表当前只包含：

- `DN`
- `StoryDiffusion`
- `SDM-v2`
- `IC-LoRA`

## 2. DN full-ready next-turn 正式结果

DN 这轮新增的正式 next-turn 结果，分成两套：

### normal20
- `D:\Projects\DN\experiments\benchmark\standard_runs\benchmark_v14_fullready_nextturn_normal20.json`
- 含义：使用生产态预生成链路，但把玩家停留时间压到 `0s`，因此基本不吃 read-wait 带来的预生成收益
- 用途：进入严格主表，与图像 baseline 的 formal20 next-turn 表并列

### pregen60s20
- `D:\Projects\DN\experiments\benchmark\standard_runs\benchmark_v14_fullready_nextturn_pregen60s20.json`
- 含义：开启预生成，并模拟玩家每 `60s` 点击一次
- 用途：展示 DN 机制收益，不直接替代严格主表中的 normal20

### DN 汇总文件
- `D:\Projects\DN\experiments\benchmark\standard_runs\benchmark_v14_fullready_nextturn_20_summary.json`
- `D:\Projects\DN\experiments\benchmark\standard_runs\benchmark_v14_fullready_nextturn_20_table.csv`

## 3. 图像 baseline formal20 仍是严格主表的参照物

这些结果依然保留，而且仍然是对照 DN 的正式图像基线：

- `D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\01_main_tables\first_turn_formal20_summary.csv`
- `D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\01_main_tables\next_turn_formal20_latency_summary.csv`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\formal20_quality_review`

原始 artifact 主目录：

- `D:\Projects\DN\remote_baseline_results_20260430\outputs\storydiffusion_formal20\storydiffusion_formal20_unstable_20260430_1200`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\storydiffusion_nextturn_formal20\storydiffusion_nextturn_formal20_unstable_v2_20260430`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\sdmv2_local_formal20\sdmv2_sdmv2_local_formal20_20260430`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\sdmv2_nextturn_formal20\sdmv2_sdmv2_nextturn_formal20_20260430`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\iclora_formal20_real\ic-lora_real_20260430_formal20`
- `D:\Projects\DN\remote_baseline_results_20260430\outputs\iclora_nextturn_formal20_real\ic-lora_real_20260430_nextturn_formal20`

## 4. DOC baseline 目前仍是可用但降级的辅助证据

DOC 目前的可用状态是：

- 已接入统一 schema
- 已产出 smoke3 / formal8 / formal20 artifacts
- 当前主用路径是 faithful fallback，不是 upstream GPT3 / Alpa / OPT 全量复现

当前最常用路径：

- `D:\Projects\DN\remote_baseline_results_20260430\doc_formal20\20260430_150320`
- `D:\Projects\DN\experiments\baseline_integration\normalized_runs\doc_yunwu\formal20_first_playable_20260430_complete`

## 5. 旧文本 playable-latency 表继续保留，但已降级

下面这些表现在应该被解释为“历史文本效率参考”，而不是严格主表：

- `D:\Projects\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\main_playable_latency_scaffold_2026-04-26.csv`
- `D:\Projects\DN\experiments\paper_method_view\1_table1_main_visual_efficiency\summary_tables\supplementary_playable_latency_worldgeneration_2026-04-26.csv`

这组表回答的是：

- 文本 playable response 多快
- DN 与 LIGHT / PWR / GenAgents 这类文本系统相比处于什么位置

这组表不再和图像 formal20 next-turn 主表并列宣称为“同口径主实验”。

## 6. 明确不是主结果 ground truth 的内容

这些内容都应该保留，但在汇报里必须降级展示：

- smoke3 runs
- formal8 runs
- blocker runs
- public SD v1.4 sanity fallback
- IC-LoRA probe / repair history
- 仅为 integration 方便产生的 normalized copies

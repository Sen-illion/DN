# MASTER_SUMMARY

## 这份摘要怎么用

这份文件的目的不是“把所有表并排堆在一起”，而是先把口径分清，再告诉你每张表该怎么引用。

## 一、现在最重要的口径变化

过去比较容易混淆的是：

- 一组表在测文本 playable response
- 另一组表在测图像 next-turn continuation

现在已经明确拆开：

### 1. 严格主实验

严格主实验只回答一个问题：

- 玩家点击后，到下一轮内容真正可交付为止，要等多久

当前对应表：

- `strict_fullready_main_comparison_2026-05-01.csv`

当前成员只有：

- `DN`
- `StoryDiffusion`
- `SDM-v2`
- `IC-LoRA`

### 2. 历史文本参考

历史文本参考继续保留，但已经降级：

- `main_playable_latency_scaffold_2026-04-26.csv`
- `supplementary_playable_latency_worldgeneration_2026-04-26.csv`

它们回答的是：

- 文本 playable latency 多快
- DN 和 LIGHT / PWR / GenAgents 这些文本系统大致差多少

它们不再和严格主实验表混写成同一层结论。

## 二、表之间的关系

### A. 新的严格主表

- `strict_fullready_main_comparison_2026-05-01.csv`

用途：

- 给老师、组会、论文主结果页一个最干净的 next-turn 对比入口
- 先看谁是同一层要比较的成员
- 再决定是否补讲历史文本参考表

### B. DN 自己的 full-ready 数据源

- `benchmark_v14_fullready_nextturn_normal20.json`
- `benchmark_v14_fullready_nextturn_pregen60s20.json`
- `benchmark_v14_fullready_nextturn_20_summary.json`
- `benchmark_v14_fullready_nextturn_20_table.csv`

用途：

- `normal20` 进入严格主表
- `pregen60s20` 展示预生成机制收益
- summary / per-item 用于追溯“慢在文本、慢在图像，还是慢在尾部”

### C. 图像 baseline 正式 formal20 表

- `first_turn_formal20_summary.csv`
- `next_turn_formal20_latency_summary.csv`

用途：

- 给外部图像 baseline 的 formal20 正式结果
- 依然是最正式的图像 baseline 主表
- 同时为 strict main table 里的 baseline 行提供支撑

### D. 较早的图像探索表

- `image_baseline_summary_20260430.csv`
- `storydiffusion_expanded_summary_20260430.csv`

用途：

- 保留 smoke3 / formal8 / blocker / fallback 的过程
- 解释为什么最终 formal20 主表会选定现在这套配置

状态：

- 重要历史证据
- 不是当前主结果表

### E. DN 内部 benchmark 汇总

- `benchmark_v1_summary_metrics.csv`
- `benchmark_v1_summary_metrics.json`
- `dn_efficiency_effectiveness_summary_v1.xlsx`

用途：

- 解释 DN 自己为什么会慢
- 把 worldview / generate option / main character 等内部阶段拆开看

## 三、当前推荐的汇报顺序

### 1. 先讲严格主实验

先看：

- `strict_fullready_main_comparison_2026-05-01.csv`

推荐说法：

- 这张表是当前最严格的 next-turn 主表
- DN 行测的是“文本+图像都 ready”
- 图像 baseline 行测的是“点击后 continuation image ready”
- 所以这张表回答的是“用户点击后，要等多久系统才能继续推进”

### 2. 再讲 DN 机制收益

再看：

- `benchmark_v14_fullready_nextturn_20_summary.json`

推荐说法：

- `normal20` 是和外部 baseline 对齐的主结果
- `pregen60s20` 是 DN 特有机制收益
- 两者一起才能解释 DN 真实使用体验

### 3. 如需补背景，再讲历史文本参考

再看：

- `main_playable_latency_scaffold_2026-04-26.csv`

推荐说法：

- 这是历史文本参考组
- 可以帮助理解 DN 在文本 playable-latency 维度的位置
- 但它不是严格主表

### 4. 最后讲 DN 内部 benchmark

再看：

- `benchmark_v1_summary_metrics.csv`

推荐说法：

- DN 的瓶颈不是一个点，而是多阶段叠加
- 如果后续要优化，应该先看内部阶段，而不是只盯最后一张表

## 四、不要再混用的内容

下面这些内容都要明确降级：

- smoke3
- formal8
- blocker rows
- public SD v1.4 fallback
- DOC fallback 与 upstream-authentic 结果
- 历史文本 playable-latency 表和严格主表的口径混写

## 五、读完这份之后该看什么

- 想直接看主结果：`strict_fullready_main_comparison_2026-05-01.csv`
- 想看 DN 机制收益：`benchmark_v14_fullready_nextturn_20_summary.json`
- 想看图像样例：`..\02_sample_reviews\formal20_quality_review\index.html`
- 想追原始 artifact：`..\03_raw_artifacts\image_baselines_formal20\README.md`
- 想确认边界与风险：`..\05_status_and_history\CURRENT_GROUND_TRUTH.md`、`..\05_status_and_history\KNOWN_ISSUES.md`

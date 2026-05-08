# One-Page Summary

## 这包材料解决什么问题

这套 handoff 包的目的不是复现所有历史探索过程，而是让接手人最快分清三件事：

- 现在真正可用的主实验结果是什么
- 这些结果分别散落在哪些原始目录
- 如果要继续实验，应该从哪条线继续，而不是重新摸索 baseline 和协议

## 当前最重要的正式结果

### 1. 图像 baseline `formal20` 主实验

这是当前最值得优先使用的对比结果，分成两张主表：

- `../01_main_tables/first_turn_formal20_summary.csv`
- `../01_main_tables/next_turn_formal20_latency_summary.csv`

对应的 3 条正式图像 baseline：

- `StoryDiffusion`
- `SDM-v2`
- `IC-LoRA`

样本量统一为 `20`，并且 first-turn / next-turn 都已经跑通。

关键数字：

- first-turn mean latency
  - `StoryDiffusion`: `7.69 s`
  - `SDM-v2`: `2.847 s`
  - `IC-LoRA`: `30.06 s`
- next-turn mean latency
  - `StoryDiffusion`: `8.495 s`
  - `SDM-v2`: `2.827 s`
  - `IC-LoRA`: `30.057 s`
- next-turn success / continuity
  - 3 条 baseline 在 formal20 上当前都是 `20/20 success`
  - `continuation_success_rate = 1.0`
  - `interaction_continuity = 1.0`

结论上，这组结果回答的是：

- 在统一 DN-style 输入和统一 next-turn 动作模板下，外部图像 baseline 的生成耗时和可连续性分别如何
- 谁更快，谁更慢，谁更适合做“点击后继续生成下一张剧情图”的对照项

### 2. 代表性样例与人工审图入口

正式样例审查入口：

- `../02_sample_reviews/formal20_quality_review/index.html`

这个 review 包适合快速看：

- 首图画质
- 下一轮连续性
- 三条图像 baseline 的行为差异

### 3. DOC 文本 baseline 当前可用状态

DOC 当前是**可用于 DN comparison pipeline 的 fallback 路线**，不是 upstream 完整复现。

当前主用路径：

- `../03_raw_artifacts/doc_baseline/README.md`
- raw fallback: `D:/Projects/DN/remote_baseline_results_20260430/doc_formal20/20260430_150320`
- normalized copy: `D:/Projects/DN/experiments/baseline_integration/normalized_runs/doc_yunwu/formal20_first_playable_20260430_complete`

它的意义是：

- 现在已经能产出 schema-compliant artifact
- 可以进入统一比较流程
- 但不能被误写成“DOC 原始 GPT3/Alpa 管线已经完整复现”

## 与之前实验的关系

### DN 自身历史文本效率对比

这部分不是本轮图像 formal20 的主表，但仍然是论文和历史说明的重要材料。

主入口：

- `../01_main_tables/main_playable_latency_scaffold_2026-04-26.csv`
- `../01_main_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`

当前可直接引用的 DN 历史数字：

- `DN` first-playable proxy mean: `7.662 s`
- `LIGHT` first-playable mean: `0.41 s`
- `LIGHT` next-turn mean: `0.431 s`
- `Plan-Write-Revise` first-playable mean: `0.833 s`
- `Plan-Write-Revise` next-turn mean: `0.837 s`
- `GenAgents` first-playable mean: `9.76 s`
- `GenAgents` next-turn mean: `6.285 s`

这部分回答的是：

- DN 在“可玩输出 / next-turn 响应”协议下，与若干文本/交互 baseline 的相对位置
- 它和新的图像 formal20 对比是并列材料，不应混为同一张表

### DN 自身 benchmark 内部汇总

入口：

- `../01_main_tables/benchmark_v1_summary_metrics.csv`
- `../01_main_tables/dn_efficiency_effectiveness_summary_v1.xlsx`

当前能快速读出的内部指标包括：

- `worldview_default_20 mean = 33.657 s`
- `worldview_no_council_20 mean = 20.031 s`
- `fullchain_default_20 worldview_median = 9.003 s`
- `fullchain_default_20 generate_option_median = 0.022 s`
- `fullchain_default_20 main_character_median = 56.546 s`
- `full_success_rate = 1.0`
- `has_image_rate = 0.95`
- `option_count_ge_2_rate = 1.0`

## 当前最稳的结论边界

可以稳写的：

- 图像 baseline formal20 first-turn / next-turn 对比已经成型
- 统一 next-turn 协议已经落实到可比较 artifact
- DOC fallback 已能进入统一 schema 比较链路
- DN 历史 text playable-latency 表仍可作为另一条证据线

不能写过头的：

- 不能把 DOC 说成 upstream 完整复现
- 不能把 `image_baseline_summary_20260430.csv` 当作 formal20 最终主表
- 不能把 smoke / formal8 / public fallback 行直接和 formal20 正式行并列引用

## 接手时的最短路径

如果接手人时间很少，建议只按这个顺序看：

1. `README.md`
2. `RESULT_MAP.md`
3. `../01_main_tables/first_turn_formal20_summary.csv`
4. `../01_main_tables/next_turn_formal20_latency_summary.csv`
5. `../02_sample_reviews/formal20_quality_review/index.html`
6. `../05_status_and_history/CURRENT_GROUND_TRUTH.md`
7. `../04_repro_entrypoints/REPRO_ENTRYPOINTS.md`

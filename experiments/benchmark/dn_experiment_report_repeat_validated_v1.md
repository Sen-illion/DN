# DN 实验报告（repeat 验证后版本）

## 1. 这版报告的定位

这是一版在 repeat 验证后整理的正式结论稿。与前面阶段性报告相比，本版最大的变化是：

- 不再只根据单轮 benchmark-v1 的 A/B 结果下判断；
- 已经补做了 `benchmark_v1 worldview default 20` 与 `benchmark_v1 worldview no_council 20` 的 repeat；
- 因此关于 `no_council` 在 worldview 阶段是否更快，已经有了更可信的结论。

本版仍然坚持只使用主角图修复后的 post-fix 数据。

## 2. 旧数据作废范围

以下历史数据仍全部作废，不纳入任何分析：

- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_baseline_results.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_no_council_results.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_comparison_summary.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\run_simple_experiment_output.txt`

原因不变：这些结果产生于主角图像生成存在问题的阶段，会干扰后续全链路实验有效性。

## 3. 当前实验体系已经补齐的部分

### 3.1 统一质量基准集

已建立：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\dn_quality_benchmark_v1.json`

特点：

- 固定 20 题；
- 按 `realistic / cyberpunk / ink_painting / watercolor / anime / oil_painting` 分层抽样；
- 每题都定义了：
  - 预期题材
  - 预期语气
  - 必须满足条件
  - 禁止问题

这解决了“输入集不统一”的问题。

### 3.2 人工评分协议

已建立：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\dn_human_rating_template_v1.xlsx`

评分维度：

- `theme_alignment_1to5`
- `narrative_coherence_1to5`
- `option_actionability_1to5`
- `visual_consistency_1to5`
- `artifact_cleanliness_1to5`
- `playable_0or1`
- `image_usable_0or1`
- `major_error_0or1`

这解决了“没有统一人工评分协议”的问题。

### 3.3 自动效果代理指标

已建立：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\compute_effectiveness_proxies.py`

当前可自动统计：

- worldview 成功率
- 首段剧情成功率
- 图片返回率
- 主角图完成率
- fallback 触发率
- scene prompt pollution rate
- protagonist prompt pollution rate

这解决了“没有自动效果护栏”的问题。

## 4. 已完成的实验

### 4.1 实验 A：benchmark-v1 上的 worldview A/B

已完成 4 组运行：

- `benchmark_v1_worldview_default_20.json`
- `benchmark_v1_worldview_default_20_repeat.json`
- `benchmark_v1_worldview_no_council_20.json`
- `benchmark_v1_worldview_no_council_20_repeat.json`

repeat 验证汇总：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_ab_repeat_validation_summary.json`

### 4.2 实验 B：benchmark-v1 上的 full-chain default

已完成：

- `benchmark_v1_fullchain_default_20.json`

### 4.3 现成的早期 post-fix 效率实验

仍保留并有效：

- 早期 full-chain 扩样 12 局
- default vs no_council 小样本 worldview 对比
- default 并发吞吐实验

但从“当前最可信结论”的角度，优先级最高的是 benchmark-v1 repeat 验证结果。

## 5. 当前最可信的稳定结论

### 5.1 worldview 阶段：no_council 已表现出稳定效率优势

这是当前最重要的新结论。

#### default 第 1 轮

- mean `33.657s`
- median `23.664s`
- p95 `68.872s`

#### default 第 2 轮

- mean `42.008s`
- median `37.517s`
- p95 `81.880s`

#### no_council 第 1 轮

- mean `20.031s`
- median `14.938s`
- p95 `44.556s`

#### no_council 第 2 轮

- mean `20.456s`
- median `18.939s`
- p95 `37.838s`

#### 合并 40 局后的对比

default：

- mean `37.832s`
- median `30.002s`
- p95 `81.879s`

no_council：

- mean `20.244s`
- median `16.046s`
- p95 `40.133s`

#### 逐题配对结果

第 1 轮：

- default 更快：3 题
- no_council 更快：17 题

第 2 轮：

- default 更快：4 题
- no_council 更快：16 题

#### 判断

基于两轮 repeat，当前可以把以下结论视为高可信：

- 在 `DN-quality-benchmark-v1` 上，`no_council` 在 worldview 阶段具有稳定效率优势；
- 这种优势同时体现在：
  - 平均值
  - 中位数
  - p95
  - 逐题配对占优次数

### 5.2 full-chain default：链路稳定，可作为现阶段对照基线

`benchmark_v1_fullchain_default_20.json` 的结果：

- worldview median `9.003s`
- generate-option median `0.022s`
- main-character median `56.546s`
- full success `20/20`

这说明：

- 修复后 full-chain default 运行稳定；
- 首段剧情的典型路径仍然很快；
- 主角图完成仍是体感上的慢段；
- 可以把当前 full-chain default 作为后续配置比较的对照基线。

### 5.3 质量护栏目前没有出现明显红灯

当前自动效果代理统计显示：

- worldview 成功率 = 1.0
- first scene 成功率 = 1.0
- image return rate = 1.0
- main character completion rate = 1.0
- fallback trigger rate = 0.0

这说明在现有 post-fix 样本上，至少“基本可玩性”层面没有看到明显回退。

## 6. 当前不能写死的结论

虽然本轮 repeat 大幅提升了结论可信度，但以下问题仍不能直接下最终结论。

### 6.1 no_council 是否适合整个 full-chain

目前只稳定证明了：

- `no_council` 在 worldview 阶段更快

但还没有证明：

- 它在 full-chain 上也更优
- 它不会引入更多质量问题

因此现在不能直接建议把整个系统默认模式全部切到 `no_council`。

### 6.2 no_council 是否会损害质量

当前只有自动效果护栏，没有完成人工评分对照。

所以还不能回答：

- 更快是否换来了更差的世界观质量
- 图文一致性是否下降
- 选项可推进性是否受影响

### 6.3 no_council 在并发场景是否仍优

目前并发实验只在 default 上完成。

因此还不能回答：

- 在 provider 队列压力下，no_council 是否仍保有优势

## 7. 对当前系统状态的总体判断

如果只看当前已经稳定的证据，可以给出如下判断：

### 7.1 效率层面

- DN 的 full-chain 已经从“修 bug 阶段”进入“可系统优化阶段”；
- worldview 与主角图仍是主要慢段；
- `no_council` 在 worldview 阶段很值得继续保留为重点优化配置。

### 7.2 评测层面

- 现在已经不再缺：
  - benchmark
  - 评分模板
  - 自动效果护栏
  - 标准化 runner
- 也就是说，DN 实验体系已经从“临时实验”升级成“可重复 benchmark 流程”。

### 7.3 结论层面

当前最适合写进正式结果部分的一句核心结论是：

> 在固定 `DN-quality-benchmark-v1` 上，`no_council` 在 worldview 生成阶段经过两轮 repeat 验证，表现出稳定且显著的效率优势；同时 default full-chain 在 20 个 benchmark 样本上保持 100% 成功运行。  

## 8. 建议的下一步

如果继续做研究推进，我建议按优先级这样走：

### 第一优先级

- 做 `full-chain no_council 20`
- 与 `full-chain default 20` 比较

这是当前最大的信息缺口。

### 第二优先级

- 对 benchmark-v1 抽样做人工评分
- 至少比较：
  - full-chain default
  - worldview default
  - worldview no_council

### 第三优先级

- 做 no_council 的并发实验
- 看它在高负载下是否仍占优

## 9. 关键文件索引

### 9.1 最终结论索引

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\dn_current_best_conclusions_v1.json`

### 9.2 repeat 验证汇总

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_ab_repeat_validation_summary.json`

### 9.3 标准化 Excel 汇总

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_standard_run_summary.xlsx`

### 9.4 人工评分模板

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\dn_human_rating_template_v1.xlsx`

### 9.5 效率+效果联合汇总

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\dn_efficiency_effectiveness_summary_v1.xlsx`

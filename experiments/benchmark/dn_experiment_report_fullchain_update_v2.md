# DN 实验报告（加入 full-chain no_council 对比后的更新版）

## 1. 本次更新的重点

在上一版 repeat 验证报告中，我们已经确认：

- `no_council` 在 `benchmark_v1` 的 worldview 阶段具有稳定效率优势。

本次新增实验则回答了一个更关键的问题：

- 这个优势能不能转化成更好的 full-chain 体验？

答案是：

**当前证据显示不能直接转化。**

更具体地说：

- `no_council` 在 worldview 单点实验中更快；
- 但在 `benchmark_v1 full-chain 20` 中，它没有比 default 更好；
- 相反，当前批次里 default 仍然是更稳妥的 full-chain 基线。

## 2. 本次新增实验

新增原始结果：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\standard_runs\benchmark_v1_fullchain_no_council_20.json`

新增汇总：

- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_fullchain_ab_summary.json`
- `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_fullchain_ab_20.csv`

## 3. full-chain default vs no_council 结果

### 3.1 default full-chain 20

- worldview
  - mean `12.458s`
  - median `9.003s`
  - p95 `30.515s`
- generate-option
  - mean `7.662s`
  - median `0.022s`
  - p95 `17.716s`
- main-character
  - mean `55.912s`
  - median `56.546s`
  - p95 `77.015s`
- success
  - `20/20`

### 3.2 no_council full-chain 20

- worldview
  - mean `16.547s`
  - median `13.799s`
  - p95 `34.737s`
- generate-option
  - mean `6.732s`
  - median `0.026s`
  - p95 `24.638s`
- main-character
  - mean `57.718s`
  - median `48.452s`
  - p95 `98.006s`
- success
  - `19/20`

### 3.3 逐题配对结果

- worldview
  - default 更快：14 题
  - no_council 更快：6 题
- generate-option
  - default 更快：9 题
  - no_council 更快：11 题
- main-character
  - default 更快：9 题
  - no_council 更快：11 题

## 4. 如何解释这个结果

这批数据说明：

- `no_council` 在 worldview 单点实验上的优势，并没有自然延伸到 full-chain。
- 在 full-chain 中，worldview 只是其中一个环节；
- 实际体验还受到：
  - `/generate-option`
  - 预生成与缓存命中
  - 主角图异步完成
  - provider 实时队列
  - 运行窗口波动
  的共同影响。

因此当前最合理的解释是：

> `no_council` 是一个在 worldview 阶段有效的单点效率优化，但它还不是一个已经证明适合直接替换 full-chain 默认配置的全链路优化。  

## 5. 本次观察到的具体风险

### 5.1 成功率风险

`no_council full-chain 20` 中出现了 1 个未完成样本：

- 样本：`DNQBV1_009`
- 主题：`茶肆说书人`
- 情况：
  - worldview 成功
  - generate-option 成功
  - 但主角图在轮询窗口内始终停留在 `generating`

这意味着：

- `no_council` 至少在当前这轮 full-chain 里，并没有比 default 更稳。

### 5.2 worldview 中位数反而落后

尽管 `no_council` 在单点 worldview 实验里更快，但在 full-chain 这轮里：

- default worldview median `9.003s`
- no_council worldview median `13.799s`

这进一步说明：

- full-chain 中的行为不能直接由单点 worldview 实验外推。

## 6. 当前最可信的结论更新

### 6.1 已稳定结论

#### 结论 A

在 `benchmark_v1 worldview` 上，`no_council` 经过两轮 repeat 验证，具有稳定效率优势。

#### 结论 B

在 `benchmark_v1 full-chain` 上，default 目前仍是更稳妥的配置基线。

理由：

- full-chain worldview 中位数更低；
- 成功率更高；
- 没有出现当前批次里的主角图超时未完成问题。

#### 结论 C

因此当前最合适的配置判断不是：

- “直接全链路切到 no_council”

而是：

- “把 no_council 视为 worldview 阶段的有效局部优化选项，但 full-chain 默认配置暂不建议直接替换”

### 6.2 仍待验证结论

- no_council 是否在进一步调优后能成为 full-chain 最优配置
- no_council 是否在人工质量评分中保持不退化
- no_council 在并发场景下是否更优

## 7. 当前推荐的配置策略

如果现在就需要一个工程决策，我的建议是：

### 短期

- full-chain 默认继续保留 `default`
- 同时把 `no_council` 作为 worldview 阶段候选优化配置继续观察

### 中期

重点做 2 件事：

1. 归因分析：为什么 no_council 单点 worldview 更快，但 full-chain 不占优
2. 质量验证：用人工评分协议比较 default 与 no_council 的质量差异

## 8. 结论压缩版

如果你要写在论文/汇报摘要里，当前最准确的一句话是：

> `no_council` 在固定 benchmark 上对 worldview 生成具有稳定的单点效率优势，但该优势尚未转化为更优的 full-chain 体验；当前 default 仍是更稳妥的全链路基线配置。  

## 9. 关键文件

- 最新结论 JSON：
  - `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\dn_current_best_conclusions_v2.json`
- full-chain 对比汇总：
  - `C:\Users\zhang\Desktop\DN\experiments\benchmark\outputs\benchmark_v1_fullchain_ab_summary.json`
- 最新结论报告：
  - `C:\Users\zhang\Desktop\DN\experiments\benchmark\dn_experiment_report_fullchain_update_v2.md`

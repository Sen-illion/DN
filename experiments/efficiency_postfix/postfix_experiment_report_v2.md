# DN post-fix 效率实验正式报告（2026-04-19）

## 1. 结论先行

- 本轮报告只使用主角图像生成修复后的真实执行数据。
- 修复后，主角图像生成链路在技术上已恢复：生成、保存、状态轮询、前端读取均可正常完成，且不再出现此前会破坏实验有效性的主角图异常。
- 三组效率实验均已完成可执行部分，且都拿到了真实运行数据：
  - 实验 1：全链路交互延迟，已扩样到 12 局。
  - 实验 2：default vs `EXPERIMENT_NO_COUNCIL=1`，各 8 个主题。
  - 实验 3：并发/吞吐，完成并发 1 / 3 / 5 三档。
- 当前 DN 的主要效率瓶颈不是本地逻辑本身，而是远端 provider 的队列等待、世界观生成长尾、以及主角图异步完成时间。
- 在本轮数据下，`no_council` 并没有表现出稳定提速，反而显示出更重的长尾和更差的队列稳定性。
- 在本轮并发实验下，并发 3 的吞吐最高；并发 5 已明显进入队列放大区间，吞吐反而退化。

## 2. 实验前提与数据作废说明

### 2.1 修复前数据全部作废

以下旧数据来自主角图像生成存在缺陷的阶段，已全部作废，不再用于任何结论：

- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_baseline_results.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_no_council_results.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\worldview_comparison_summary.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_phase1\run_simple_experiment_output.txt`

作废原因：

- 当时主角图像生成链路异常，会直接影响全链路实验的有效性；
- 旧数据无法区分“系统真实效率问题”和“主角图生成 bug 造成的异常等待/异常结果”；
- 因此旧结果不能再作为 post-fix 阶段的对比基准。

### 2.2 本轮有效数据范围

本轮只使用以下 post-fix 数据：

- 主角修复验证：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\protagonist_fix_verification_runtime.json`
- 实验 1（全链路，4 局旧 post-fix 样本）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v2_4themes.json`
- 实验 1（全链路，新增 8 局样本）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v3_8themes.json`
- 实验 1（12 局合并汇总）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_combined_12themes_summary.json`
- 实验 2（default）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_default_v2_8themes.json`
- 实验 2（no_council）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_no_council_v2_8themes.json`
- 实验 3（并发/吞吐）：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\concurrency_default_v1_6themes_1_3_5.json`
- 最新总索引：`C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\postfix_suite_summary_v3.json`

## 3. 如何确认主角图像生成修复确实生效

### 3.1 技术链路检查

已检查的关键代码点包括：

- `C:\Users\zhang\Desktop\DN\src\image\prompt_optimize.py`
- `C:\Users\zhang\Desktop\DN\src\image\api_providers.py`
- `C:\Users\zhang\Desktop\DN\game_server.py`

确认点：

- 主角图 prompt 在进入 provider 前会做风格归一化；
- 主角图请求走独立 `request_type="main_character"`；
- 服务端提供 `/main-character-status/<game_id>` 轮询接口；
- 主角图资源读取链路加了 no-cache 处理，减少前端误判。

### 3.2 真实运行验证

基于 `protagonist_fix_verification_runtime.json` 的真实执行结果：

- 主角图状态从 `generating` 正常推进到 `completed`；
- `metadata.json` 成功写入；
- 主角图可以通过 `/initial/main_character/.../main_character.png` 获取；
- 本轮验证中未再出现旧问题里常见的异常报错；
- 主角图已能被后续剧情图链路作为参考输入正常使用。

### 3.3 仍存在的残余问题

虽然技术链路已恢复，但仍观察到个别主角 prompt 存在语义污染或设定串场的问题。其影响范围主要是：

- 会影响“图像语义纯净度/设定一致性”判断；
- 对本轮“效率、时延、队列、吞吐”结论影响较小；
- 因此本轮结果适合做效率结论，不适合直接当作高置信度质量结论。

## 4. 实验设计口径

### 4.1 统一实验对象

- 主要对象：Web 全链路
- 服务入口：`game_server.py`
- 主要 API：
  - `/generate-worldview`
  - `/generate-option`
  - `/main-character-status/<game_id>`

### 4.2 统一观测指标

- `worldview_elapsed_s`
- `generate_option_elapsed_s`
- `main_character_completion_s`
- provider `queue_wait_ms`
- provider `latency_ms`
- `throughput_runs_per_min`
- 成功率、是否返回 scene、是否返回 image

### 4.3 统一限制

- 真实调用远端 provider，结果受外部队列与服务状态影响；
- 绝对时长会波动；
- 因此结论以“分布、中位数、p95、长尾、吞吐趋势”为主，而不只看单次均值。

## 5. 实验 1：全链路交互延迟实验

### 5.1 目标

验证 post-fix 条件下，从世界观生成到首段剧情返回，再到主角图异步完成的全链路真实等待情况。

### 5.2 实验配置

- 配置：default
- 样本：12 个主题
- 数据文件：
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v2_4themes.json`
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v3_8themes.json`
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_combined_12themes_summary.json`

### 5.3 合并结果

- `worldview_elapsed_s`
  - 均值：`32.426s`
  - 中位数：`11.600s`
  - p95：`120.454s`
  - 最大值：`192.806s`
- `generate_option_elapsed_s`
  - 均值：`12.777s`
  - 中位数：`0.021s`
  - p95：`74.472s`
  - 最大值：`97.474s`
- `main_character_completion_s`
  - 均值：`72.156s`
  - 中位数：`62.468s`
  - p95：`156.009s`
  - 最大值：`183.835s`
- provider `queue_mean_ms`
  - 均值：`1889.589ms`
  - 中位数：`1100.141ms`
  - p95：`6108.458ms`
- 成功情况
  - 12/12 全部成功
  - 12/12 都返回 scene
  - 12/12 都返回 image
  - 12/12 主角图最终都可用

### 5.4 关键观察

- `generate-option` 的典型值非常低，中位数仅 `0.021s`，说明首段剧情常常能从缓存/预生成路径快速命中。
- 但 `generate-option` 也存在明显长尾，最大达到 `97.474s`，说明该链路不是“稳定快”，而是“多数快、少数极慢”。
- `worldview` 的中位数仅 `11.6s`，但均值被长尾拉到 `32.4s`，最大值 `192.8s`，长尾非常突出。
- 主角图完成时间中位数约 `62.5s`，这是当前全链路用户感知里最稳定的“慢段”之一。
- 出现一次 `main_character_s = 0.023s` 的情况，说明该局在轮询时主角图已处于可完成状态，不能把它理解为主角图本身只耗时 0.023 秒；这是轮询观测粒度造成的偏差。

### 5.5 结论

- 修复后，全链路可稳定跑通，这一点现在可以认为是可信结论。
- 对用户体验影响最大的效率问题，依然是：
  - `worldview` 长尾；
  - 主角图异步完成时间；
  - 少数情况下 `generate-option` 慢路径。
- 因此后续要提升“首屏体验”，优先级应是：
  1. 降低 `worldview` 长尾；
  2. 缩短主角图完成时间或进一步弱化其首屏感知影响；
  3. 查明 `generate-option` 极端慢路径触发条件。

## 6. 实验 2：default vs no_council 效率对比

### 6.1 目标

验证关闭 council 后是否真的能带来更稳定、更快的世界观生成效率。

### 6.2 实验配置

- 对照组：default
- 比较组：`EXPERIMENT_NO_COUNCIL=1`
- 样本：相同 8 个主题
- 数据文件：
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_default_v2_8themes.json`
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_no_council_v2_8themes.json`

### 6.3 结果

#### default

- 平均：`22.642s`
- 中位数：`21.477s`
- p95：`28.677s`
- 每轮 provider 队列等待均值：`4522.715ms`
- 成功率：`8/8`

#### no_council

- 平均：`45.744s`
- 中位数：`23.582s`
- p95：`114.913s`
- 每轮 provider 队列等待均值：`45764.277ms`
- 成功率：`8/8`

### 6.4 配对观察

按同一主题逐对比较：

- default 更快：4 次
- no_council 更快：4 次

但需要注意：

- no_council 的慢局更慢；
- no_council 的队列等待显著更高；
- no_council 的均值和 p95 都明显更差。

### 6.5 结论

- 在本轮 post-fix 数据下，`no_council` 不能被视为稳定加速方案。
- 它在部分主题上会更快，但整体表现更不稳定，尾部风险明显更高。
- 若目标是“默认面向真实玩家的稳定体验”，当前更推荐保留 default，而不是直接切到 `no_council`。

## 7. 实验 3：并发 / 吞吐实验

### 7.1 目标

验证系统在不同并发下的吞吐、队列等待和单次延迟如何变化，找出当前可接受的服务负载区间。

### 7.2 实验配置

- 配置：default
- 样本：6 个主题
- 并发档位：1 / 3 / 5
- 数据文件：
  - `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\concurrency_default_v1_6themes_1_3_5.json`

### 7.3 结果

#### 并发 1

- 总墙钟：`222.569s`
- 吞吐：`1.617 runs/min`
- 单次均值：`37.095s`
- 单次 p95：`68.954s`
- 队列均值：`11641.721ms`
- 队列 p95：`29711.0ms`

#### 并发 3

- 总墙钟：`129.412s`
- 吞吐：`2.782 runs/min`
- 单次均值：`61.178s`
- 单次 p95：`105.525s`
- 队列均值：`20789.962ms`
- 队列 p95：`58288.0ms`

#### 并发 5

- 总墙钟：`225.036s`
- 吞吐：`1.600 runs/min`
- 单次均值：`88.004s`
- 单次 p95：`188.732s`
- 队列均值：`55198.241ms`
- 队列 p95：`127136.1ms`

### 7.4 结论

- 当前最优吞吐点落在并发 3 左右，而不是并发 5。
- 从并发 3 升到并发 5 后：
  - 吞吐没有继续提升；
  - 单次时延显著恶化；
  - provider 队列等待急剧上升；
  - 系统进入明显的排队放大区间。
- 因此，当前 DN 在真实服务场景下更接近“provider 队列约束系统”，而不是简单的“本地 CPU 约束系统”。

## 8. 三组实验分别说明了什么

### 实验 1 说明了什么

- post-fix 后 DN 已能稳定跑通完整起局链路；
- 首段剧情多数能很快返回；
- 真正影响体感的是世界观长尾和主角图完成时间。

### 实验 2 说明了什么

- `no_council` 不是稳定收益配置；
- 它没有在本轮样本里表现出清晰的一致性提速；
- 反而在尾部时延和队列等待上更差。

### 实验 3 说明了什么

- 当前系统存在明显的并发阈值；
- 并发不是越高越好；
- 超过一定负载后，排队等待会吞掉所有并发收益。

## 9. 可信度判断

### 9.1 可以认为可信的部分

- 主角图修复后的技术链路恢复；
- post-fix 条件下全链路可完成；
- default vs no_council 的稳定性差异；
- 并发 3 优于并发 5 的吞吐拐点。

### 9.2 仍需谨慎的部分

- 全链路虽然已扩到 12 局，但若要形成更正式 benchmark，仍建议继续扩样；
- 结果受 provider 实时状态影响，绝对秒数不能简单视作固定常数；
- 主角 prompt 残余语义污染意味着，本轮不适合对图像质量或剧情一致性做强结论。

## 10. 建议的下一步

### 10.1 若继续做效率优化验证

建议新增两类实验：

- 固定时段重复实验：区分“系统真实改进”和“provider 当时空闲”
- 世界观长尾归因实验：拆分 prompt 长度、provider 排队、缓存命中、重试次数

### 10.2 若准备把效率实验做成正式论文/汇报材料

建议补齐：

- 统一机器资源记录（CPU / 内存）
- token / 调用数 / 图片请求数统计
- 抽样质量约束指标
- 统一时段与重复轮次

## 11. 文件索引

### 11.1 总索引

- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\postfix_suite_summary_v3.json`

### 11.2 正式报告

- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\postfix_experiment_report_v2.md`

### 11.3 核心原始数据

- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\protagonist_fix_verification_runtime.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_default_v2_8themes.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\worldview_no_council_v2_8themes.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v2_4themes.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_v3_8themes.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\fullchain_default_combined_12themes_summary.json`
- `C:\Users\zhang\Desktop\DN\experiments\efficiency_postfix\concurrency_default_v1_6themes_1_3_5.json`

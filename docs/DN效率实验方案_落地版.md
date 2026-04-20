# DN 效率实验方案（落地版）

本文档面向 `C:\Users\zhang\Desktop\DN` 当前仓库，目标不是泛泛讨论“性能优化”，而是给出一套能直接开跑、能直接沉淀结果、并且和现有代码结构对齐的效率性实验方案。

先说明两点前提：

- 本方案优先服务 **Web 主链路的全链路体验**，因为当前 DN 最典型的运行方式是 `game_server.py` + `game-frontend/`。
- 当前仓库已经具备一批可以立即利用的观测点：`logs/provider_events.jsonl`、`logs/provider_events_summary.*`、`server/experiment_log.py`、`DN-experiment/`、`test_speed.py`、`DN-experiment/run_simple_experiment.py`、`DN-experiment/run_batch_themes.py`。

当前仍缺少但不阻塞初版的前置信息：

- 没有统一的 CPU / GPU / 内存采样脚本，因此资源消耗暂时作为“建议补充指标”，不作为初版强制门槛。
- 没有统一的质量基准集或人工评分协议，因此“效果”先用可推进率、图片返回率、兜底率、人工抽样复核来约束。
- 没有单价配置，因此“成本”先按 token、LLM 调用次数、图片请求次数、单位完成局耗时做代理指标。

---

## 一、DN 项目运行机制梳理

### 1. 项目整体架构

DN 目前是一个 **CLI + Flask Web 双运行模式** 的 AI 驱动叙事游戏系统，核心链路可以概括为：

`前端/CLI -> game_server.py 或 TextAdventureGame -> main2.py 聚合层 -> src/llm + src/story + src/image + src/characters -> 外部 LLM / 图像 API -> 本地缓存 / 实验目录 / 日志`

按层拆开看：

1. **入口层**
   - CLI 入口：`main.py`
   - Web 入口：`game_server.py`
   - 生产化启动壳：`start_server.py`

2. **聚合层**
   - `main2.py` 负责把 `src/` 中拆分后的世界观、剧情、结局、图像等能力重新汇总出来，供 CLI 和 Web 共用。

3. **核心逻辑层**
   - `src/llm/`：世界观与剧情文本生成
   - `src/story/`：选项推进、结局、图文组合流程
   - `src/image/`：提示词优化、场景图/主角图生成、缓存、下载、存储
   - `src/characters/`：主角/配角档案、参考图、角色归档
   - `src/worldview/`：模板、缓存、结构化解析
   - `src/game/`：CLI 主循环
   - `src/wiki/`：现实题材或 IP 信息补充

4. **Web 服务辅助层**
   - `server/cache.py`：预生成缓存与锁
   - `server/pregeneration.py`：两层选项预生成
   - `server/provider_control.py`：provider 并发门控、排队与事件日志
   - `server/events.py`：SSE 推送
   - `server/experiment_log.py`：实验过程落盘

5. **前端层**
   - `game-frontend/script-modular.js` 负责调 `game_server.py` 暴露的 API，组织“主菜单 -> 世界观生成 -> 剧情推进 -> 预生成 -> 存档/结局”的浏览器链路。

### 2. 核心模块及其职责

#### 2.1 世界观生成

- `src/llm/global_gen.py`
- 负责根据主题、主角属性、难度、基调生成 `global_state`
- 包含：
  - 分阶段世界观生成
  - 模板/缓存补全
  - 单模型调用
  - Council 群体智能切换
  - `PERF_*` token 配置

这里是 **首屏冷启动** 的关键耗时来源之一。

#### 2.2 Council 群体智能

- `src/llm/council_core.py`
- 当前是典型的三阶段结构：
  1. 多模型并行生成
  2. 多模型匿名互评
  3. 主席模型综合输出

这条链路天然会显著增加：

- LLM 请求次数
- 总 token 消耗
- 排队时间
- 端到端首屏时长

因此它非常适合作为“效率-效果权衡实验”的核心自变量。

#### 2.3 单轮剧情与选项推进

- `src/story/options.py`
- `_generate_single_option()`：执行某个选项，返回新场景、下一组选项、剧情图
- `_generate_single_option_text_only()`：只生成文本，适合和图像并行分拆
- `generate_all_options()`：生成多个选项内容，内含图片并发生成

这里是 **轮级响应时延** 的核心模块。

#### 2.4 图像生成链路

- `src/image/api_providers.py`
- `generate_scene_image()` 提供：
  - 场景图提示词优化
  - 参考图支持
  - provider 切换
  - 本地缓存
  - prompt 缓存
  - 下载落盘
  - 超时与重试

与效率最相关的点包括：

- 图片 provider 的排队和延迟
- `use_cache` 与 `skip_cache_lookup`
- 场景提示词缓存 `_scene_prompt_cache`
- 多线程出图的 worker 数
- 是否等待主角参考图准备完成

#### 2.5 Web 预生成与缓存

- `server/pregeneration.py`
- `server/cache.py`
- `game_server.py` 中 `/pregenerate-next-layers`、`/generate-option`

当前 Web 体验并不是纯同步串行，而是：

1. 用户在读当前剧情
2. 后端后台生成下一层文本/图片
3. 用户点击时优先命中缓存

这决定了 DN 的效率实验不能只测单个 API，而必须测：

- 预生成命中率
- 文本先返回、图片后补齐的比例
- 缓存命中与缓存污染
- 锁等待与排队

#### 2.6 Provider 门控与事件日志

- `server/provider_control.py`
- `src/llm/api.py`
- `src/image/api_providers.py`

当前仓库已经把效率实验最重要的一类指标结构化落盘到了 `logs/provider_events.jsonl`：

- `queue_wait_ms`
- `latency_ms`
- `kind`
- `provider`
- `request_type`
- `status`
- `priority`

并可通过 `scripts/analyze_provider_events.py` 汇总为：

- `logs/provider_events_summary.md`
- `logs/provider_events_summary.json`
- `logs/provider_events_summary.csv`

这是当前最适合做 **排队时间 / 服务时延 / 并发瓶颈** 实验的数据源。

#### 2.7 实验落盘

- `server/experiment_log.py`
- `DN-experiment/experiment_save.py`

当前游戏可以把剧情段、场景图、prompt、scene 文本等写到 `DN-experiment/<game_id>/` 下，便于后续：

- 追溯单局链路
- 做文本/图像抽样
- 统计图片返回率
- 对照不同配置的具体产物

### 3. 游戏运行主流程

Web 模式是效率实验默认对象，主流程如下：

1. 启动服务：`python game_server.py` 或 `python start_server.py`
2. 前端向 `/generate-worldview` 提交主题、主角属性、难度、基调
3. 后端调用 `llm_generate_global(...)` 生成 `global_state`
4. 系统生成首段剧情与首组 `next_options`
5. 同时触发首轮预生成
6. 用户点击一个选项，前端请求 `/generate-option`
7. 后端优先查预生成缓存：
   - 命中：直接返回或返回“文本已完成、图片待补”
   - 未命中：现场生成
8. 返回新场景、下一组选项、剧情图或补图状态
9. 前端继续触发 `/pregenerate-next-layers`
10. 达到条件后调用 `/generate-ending`
11. 可随时走 `/save-game`、`/load-game`、`/list-saves`

CLI 模式由 `src/game/adventure.py` 驱动，流程与 Web 类似，但少了浏览器和 API 调用层，适合做纯文本逻辑排查，不适合作为“全链路体验”主实验对象。

### 4. 数据流与调用链

#### 4.1 文本主链路

`game-frontend/script-modular.js`
-> `/generate-worldview` 或 `/generate-option`
-> `game_server.py`
-> `main2.py` 暴露的生成函数
-> `src/llm/global_gen.py` / `src/story/options.py`
-> `src/llm/api.py`
-> 远程 LLM provider
-> 日志写入 `logs/provider_events.jsonl`

#### 4.2 图片主链路

`game_server.py`
-> `src/story/options.py`
-> `src/image/api_providers.py`
-> provider 门控与图片 API 调用
-> 下载/缓存到 `image_cache/`
-> 前端通过 `/image_cache/<filename>` 或异步补图使用

#### 4.3 实验与产物链路

`game_server.py`
-> `server/experiment_log.py`
-> `DN-experiment/<game_id>/scene_*.json + 图片`

#### 4.4 汇总分析链路

`logs/provider_events.jsonl`
-> `scripts/analyze_provider_events.py`
-> `provider_events_summary.md / json / csv`

### 5. 启动方式、配置方式、实验入口

#### 5.1 启动方式

- CLI：
  - `python main.py`
- Web：
  - `python game_server.py`
  - `python start_server.py`

#### 5.2 配置方式

主要由根目录 `.env` 控制，当前效率实验最相关的是：

- 文本模型：
  - `Camera_Analyst_MODEL`
  - `Camera_Analyst_BASE_URL`
  - `Camera_Analyst_READ_TIMEOUT`
- 图像模型：
  - `IMAGE_GENERATION_PROVIDER`
  - `Image_Generation_MODEL`
  - `YUNWU_IMAGE_TIMEOUT_SECONDS`
- Council / token /性能控制：
  - `EXPERIMENT_NO_COUNCIL`
  - `PERF_OPT_TOKENS`
  - `PERF_WORLDVIEW_TOKENS`
  - `PERF_PLOT_TOKENS_INITIAL`
  - `PERF_PLOT_TOKENS_NORMAL`
- 图片与角色链路开关：
  - `EXPERIMENT_SKIP_PROTAGONIST_REF`
  - `IMAGE_TASK_TIMEOUT_SECONDS`
  - `OPTION_WAIT_TIMEOUT_SECONDS`

为避免泄露敏感信息，实验文档只引用变量名和模型名，不引用任何密钥。

当前本地环境中可直接用于实验描述的非敏感配置是：

- 文本主模型：`gemini-3.1-flash-lite-preview`
- 图像模型：`gemini-2.5-flash-image`
- 图片 provider：`yunwu`

#### 5.3 已有实验入口

- `test_speed.py`
  - 已可测 `/generate-worldview` 的单次调用时长
- `DN-experiment/run_simple_experiment.py`
  - 最小单主题链路，适合冷启动测量
- `DN-experiment/run_batch_themes.py`
  - 批量主题双段剧情实验，适合吞吐和批处理实验
- `scripts/analyze_provider_events.py`
  - provider 队列与时延汇总

### 6. 可能影响效率表现的关键环节

DN 当前最值得纳入效率实验的环节如下：

1. **LLM 排队等待**
   - 由 `provider_request_slot` 控制
   - 对总时长影响很大

2. **LLM 真正服务时延**
   - 世界观生成
   - 单轮剧情生成
   - Council 多阶段生成

3. **图片生成与下载时延**
   - 文生图时延
   - OSS / URL 下载落盘时延
   - 图片补图延时

4. **预生成命中率**
   - 命中时用户等待显著下降
   - 未命中会退化为同步现场生成

5. **场景图缓存命中率**
   - 冷缓存与热缓存差异很大

6. **token 上限配置**
   - 直接影响文本长度、推理时长和可能的截断

7. **主角参考图等待**
   - 首屏主角图异步生成是否拖慢剧情图链路

8. **图片并发与 provider 限流**
   - `generate_all_options()` 与 `provider_control.py` 的组合会影响队列长度

9. **锁等待**
   - `cache_lock` 及预生成线程竞争，可能造成文本已出但缓存迟迟未写回

10. **SSE / 异步补图感知延迟**
   - 技术上图片已生成，不代表用户已经“看到”

### 7. 多种运行模式与配置分支

当前项目至少存在下列几种值得区分的模式：

1. **CLI vs Web**
   - CLI 更适合纯逻辑回归
   - Web 才是全链路体验实验主对象

2. **Council 开 vs 关**
   - 通过 `EXPERIMENT_NO_COUNCIL`
   - 对首屏时延和 token 消耗影响显著

3. **主角参考图参与 vs 跳过**
   - 通过 `EXPERIMENT_SKIP_PROTAGONIST_REF`
   - 对剧情图一致性和时延有直接影响

4. **冷缓存 vs 热缓存**
   - `image_cache/` 是否已命中
   - `provider_events.jsonl` 是否为新一轮实验重新归档

5. **单局交互模式 vs 批处理模式**
   - Web 单局：更看重体感延迟
   - `DN-experiment/run_batch_themes.py`：更看重吞吐和稳定性

---

## 二、相关实验方法调研总结

下面只保留对 DN 真正有借鉴意义的方法，不做论文堆砌。

### 1. 可直接借鉴的外部工作

#### 1.1 AgentBench

来源：[AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)

可借鉴点：

- 评测对象不是静态问答，而是 **交互式、多轮、带环境反馈** 的系统
- 指标不只看最终结果，还看多步过程成本

对 DN 的借鉴：

- 不能只测 `/generate-worldview`
- 必须按 **局级、轮级、阶段级** 拆指标
- 要把“走到第几轮、哪一轮卡住、哪一段变慢”纳入报告

#### 1.2 WebArena

来源：[WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)

可借鉴点：

- 固定任务集
- 固定环境
- 固定操作协议
- 强调可复现端到端流程

对 DN 的借鉴：

- 主题池必须固定
- 操作脚本必须固定
- 每局最大轮数必须固定
- 同一实验配置必须重复多次

#### 1.3 GAIA

来源：[GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)

可借鉴点：

- 评测现实任务时，同时关注效率与任务完成情况
- 多模态与工具使用会放大链路成本

对 DN 的借鉴：

- DN 不是单纯文本系统，而是 **文本 + 图像 + 缓存 + 多线程**
- 只报“更快”没有意义，必须同时报：
  - 可推进率
  - 图片返回率
  - 兜底率
  - 抽样质量复核

#### 1.4 HELM

来源：[Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)

可借鉴点：

- 不鼓励单指标评价
- 成本、延迟、质量应联合观察

对 DN 的借鉴：

- 实验结论必须至少是“双轴”的：
  - 效率轴
  - 效果轴

典型写法不是“配置 B 更优”，而是：

- 配置 B 在平均时延下降 28% 的同时，图片返回率只下降 2%，因此适合作为默认线上配置

#### 1.5 MLPerf Inference

来源：[MLPerf Inference Submission Guide](https://docs.mlcommons.org/inference/submission/)

可借鉴点：

- 按不同场景测不同指标，而不是拿同一套口径硬套所有场景
- 区分单流交互、服务端、离线吞吐等场景

对 DN 的借鉴：

DN 应拆成三类实验：

1. 单用户交互场景
2. 批量离线内容生成场景
3. 并发服务场景

这也是本文三组实验的划分依据。

### 2. 这些工作里的常见做法

#### 2.1 实验变量如何设置

常见做法是只改一类核心因素，其余保持不变。对 DN 来说，最合适的变量是：

- 是否开启 Council
- token 上限高低
- 是否等待主角参考图
- 是否启用预生成
- 冷缓存或热缓存
- 并发局数

不建议把多个强变量混在一起，否则很难解释结果来源。

#### 2.2 对照组如何设计

常见做法是：

- 用当前默认配置作为 baseline
- 每次只改一个主要因素
- 如果是强工程变量，再设计 2 到 3 个强度档位

映射到 DN：

- 默认当前 Web 运行方式作为对照组
- A/B 或 A/B/C 设计优于只跑单配置

#### 2.3 常用效率指标

对 DN 最有价值的指标包括：

- 单局总时长
- 首屏世界观生成时长
- 首轮可点击时长
- 单轮文本返回时长
- 单轮图片可见时长
- LLM 调用次数
- 图片调用次数
- token 消耗
- provider 平均排队时间
- provider p95 排队时间
- provider 平均服务时延
- 吞吐量
- 失败率 / 超时率 / 兜底率

#### 2.4 数据如何记录与汇报

常见做法是：

- 同时保留原始日志和汇总表
- 至少报告平均值、p50、p95、失败率
- 对于长链路任务，保留任务级明细

映射到 DN：

- 原始日志：`provider_events.jsonl`
- 聚合汇总：`provider_events_summary.*`
- 单局明细：`DN-experiment/<game_id>/scene_*.json`
- 请求级观测：Flask 控制台日志

#### 2.5 如何兼顾效率与效果平衡

常见做法不是“先测效率、再口头说质量还行”，而是同时设一个 **最低效果约束**。

DN 初版可采用以下效果约束：

- 平均可推进轮数不能明显下降
- 选项可用率不低于 baseline
- 图片返回率不低于 baseline
- 兜底文本触发率不能显著上升
- 每组配置人工抽样 10 到 20 局，检查明显剧情崩坏或画面错配

### 3. 对 DN 最值得借鉴的 5 条方法论

1. **固定任务集，不要临时想主题**
   - 使用 `game_themes_100.json` 作为固定主题池

2. **区分冷启动与热路径**
   - 首局冷缓存和后续热缓存必须分开统计

3. **区分交互延迟与系统吞吐**
   - 玩家体验好，不等于系统可扩展

4. **必须做 A/B 或 ablation**
   - 不能只跑单配置然后下结论

5. **效率实验必须带效果约束**
   - 否则很容易得出“跳过图片最快”这种没有实际价值的结论

---

## 三、效率实验总体设计思路

### 1. 实验目标

本轮效率实验不直接追求“把所有指标都测全”，而是围绕三个问题组织：

1. 玩家真正等待的时间主要耗在哪一段？
2. 更轻的模型/生成配置是否能在不明显伤害效果的前提下降本提速？
3. 多局并行时系统容量会在哪一层先崩？

### 2. 实验对象

默认实验对象为 **Web 主链路**，原因如下：

- 当前用户体验主要落在 Web 模式
- Web 模式同时包含：
  - API 调用
  - 预生成
  - 图片补图
  - provider 排队
  - 缓存写回
  - SSE / 前端感知延迟

CLI 可作为补充排障对象，但不作为本轮主实验对象。

### 3. 统一观测粒度

#### 3.1 局级指标

- 单局总时长
- 单局完成与否
- 单局总 LLM 调用数
- 单局总图片调用数
- 单局总 token
- 单位完成局成本代理

#### 3.2 轮级指标

- 单轮文本响应时长
- 单轮图片可见时长
- 单轮平均等待
- p50 / p95
- 单轮是否命中预生成
- 单轮是否触发兜底

#### 3.3 系统级指标

- 吞吐量
- provider 平均排队时间
- provider p95 排队时间
- provider 平均服务时延
- 错误率 / 超时率
- 缓存命中率
- 锁等待现象

### 4. 统一数据源

本轮实验统一使用以下数据源：

1. `logs/provider_events.jsonl`
   - 主数据源，用于排队时间、服务时延、失败状态

2. `logs/provider_events_summary.*`
   - 汇报与复核使用

3. `DN-experiment/<game_id>/scene_*.json`
   - 单局剧情段级明细

4. Flask 控制台日志 / `logs/backend.log`
   - 请求入口与错误定位

5. 现有脚本输出
   - `test_speed.py`
   - `DN-experiment/run_simple_experiment.py`
   - `DN-experiment/run_batch_themes.py`

如需后续补完整资源指标，可增量加入系统资源采样脚本，但不影响本版实验先执行。

### 5. 统一效果代理指标

在没有统一自动质量基准前，本轮统一使用以下效果代理：

- 完成局比例
- 平均可继续推进轮数
- 选项可用率
- 图片返回率
- 兜底文本触发率
- 人工抽样剧情/图像一致性复核

### 6. 统一分析方法

每组实验统一采用：

- 同一主题集
- 同一配置重复多次
- A/B 或 A/B/C 对比
- 输出平均值、p50、p95、失败率
- 结论写成“效率-效果双轴”

建议默认样本设计：

- 主题池：`game_themes_100.json`
- 小样本验证：10 个主题
- 正式统计：30 个主题
- 每配置重复 3 次
- 冷缓存与热缓存分开统计

### 7. 当前已知瓶颈信号

根据当前 `logs/provider_events_summary.md`，已经可以确认：

- 总体平均排队等待约 `52196.21 ms`
- 总体 p95 排队等待约 `143175 ms`
- `llm / yunwu / chat_completion`
  - 平均排队约 `65300.02 ms`
  - p95 排队约 `165014 ms`
  - 平均服务时延约 `42695.24 ms`
- `image / yunwu / scene_image`
  - 平均排队约 `13175.5 ms`
  - 平均服务时延约 `40199.73 ms`

这说明当前 DN 的主瓶颈不是单点 I/O，而是 **provider 队列等待 + 远程模型调用** 叠加。

---

## 四、3 组效率实验详细方案

## 实验 1：全链路交互延迟拆解实验

### 1. 实验名称

全链路交互延迟拆解实验

### 2. 实验目的

定位“玩家体感等待”主要耗在哪一段，并验证预生成、缓存、异步补图是否真正改善 Web 游戏体验。

### 3. 核心假设

1. 开启预生成后，非首轮的文本响应时长会显著下降。
2. 热缓存下的图片可见时长会明显短于冷缓存。
3. 图片改为异步补图后，文本首返回时长会下降，但图片完整呈现时长未必同步下降。

### 4. 自变量、因变量、控制变量

#### 自变量

- 预生成：开 / 关
- 图片策略：同步等待 / 异步补图
- 缓存状态：冷缓存 / 热缓存

#### 因变量

- 首屏世界观生成时长
- 首轮可选项出现时长
- 单轮文本返回时长
- 单轮图片可见时长
- 整局完成时长
- 预生成命中率

#### 控制变量

- 固定文本模型
- 固定图像模型
- 固定图片 provider
- 固定主题池
- 固定难度与结局基调
- 固定最大轮数

### 5. 对照组 / 比较组设置

- **对照组 A**：当前默认 Web 配置（预生成开、默认补图逻辑、冷缓存）
- **比较组 B**：关闭预生成
- **比较组 C**：保留预生成，但在统计上区分文本首返回与图片最终可见
- **比较组 D**：热缓存复跑

如果不改代码，可按“实验运行方式”近似实现：

- A：按当前正常方式跑第一遍
- B：不主动调用 `/pregenerate-next-layers`
- C：记录 `/generate-option` 文本返回时间与图片最终可见时间
- D：不清空 `image_cache/` 再跑第二遍

### 6. 实验对象与运行条件

- 对象：Web 模式下的完整用户交互链路
- 启动方式：`python game_server.py`
- 主题来源：`game_themes_100.json`
- 样本量建议：
  - 小样本：10 个主题，每主题 5 轮
  - 正式：30 个主题，每主题 5 到 8 轮
- 每组实验都分：
  - 冷缓存
  - 热缓存

### 7. 具体执行步骤

1. 备份当前 `logs/provider_events.jsonl`
2. 清理或归档本轮实验日志
3. 启动 `game_server.py`
4. 用固定主题池逐局运行 Web 主链路
5. 对每局记录：
   - `/generate-worldview` 开始和结束时间
   - 首轮文本出现时间
   - 每轮点击后文本返回时间
   - 每轮图片可见时间
   - 本轮是否命中预生成
6. 对照组 A 跑完后，执行比较组 B、C、D
7. 每组实验结束后运行：
   - `python scripts/analyze_provider_events.py`
8. 汇总局级、轮级、provider 级指标

建议直接利用现有脚本：

- 首屏世界观：`test_speed.py`
- 单局产物追踪：`DN-experiment/run_simple_experiment.py`
- 多局固定主题：参考 `DN-experiment/run_batch_themes.py`

### 8. 需要记录的数据

- game_id
- 主题 ID / 主题文本
- 轮数
- `/generate-worldview` 时长
- 每轮文本返回时长
- 每轮图片可见时长
- 是否命中预生成
- 是否命中图片缓存
- provider 排队时间
- provider 服务时延
- 是否触发兜底文本
- 是否有图片缺失

### 9. 评测指标

- 首屏平均时长、p50、p95
- 首轮可玩时长
- 单轮文本平均时长、p50、p95
- 单轮图片平均完成时长、p50、p95
- 整局总时长
- 预生成命中率
- 图片缓存命中率
- 完成局比例

### 10. 结果分析方法

1. 先做 **阶段拆解**
   - 世界观阶段
   - 首轮剧情阶段
   - 后续轮次阶段

2. 再做 **冷/热缓存对比**

3. 再对比 **文本首返回** 和 **图片完整可见**

4. 最后把结果映射到 provider 队列数据：
   - 如果文本慢但 provider 排队低，可能是 prompt / Council / token 造成
   - 如果文本慢且排队高，则优先看 provider 门控和并发

### 11. 预期现象

- 预生成开启后，后续轮次文本时长应明显下降
- 热缓存下图片返回速度明显提升
- 异步补图会显著改善“文本先出来”的体感，但图片完整时间不一定同步下降
- 首屏冷启动仍然可能是整局最大瓶颈

### 12. 潜在风险与误差来源

- 网络波动导致 provider 时延随机抖动
- 主题复杂度差异造成文本长度不一致
- 图片 provider 返回内容差异导致缓存命中不稳定
- 控制台日志时间点和前端实际可见时间存在少量偏差
- 当前未统一采样浏览器端渲染耗时，因此“图片可见时间”更接近业务链路时间，不是纯前端渲染时间

---

## 实验 2：模型/生成配置效率-效果权衡实验

### 1. 实验名称

模型与生成配置效率-效果权衡实验

### 2. 实验目的

评估更轻量的文本/图像配置是否能在尽量不伤害剧情推进和图像可用性的前提下，降低时延和调用成本。

### 3. 核心假设

1. 关闭 Council 会显著降低首屏世界观时长和总 LLM 调用数。
2. 收紧 token 上限会降低平均时延，但可能提高文本截断或剧情贫化风险。
3. 跳过主角参考图会缩短图片链路时长，但可能降低角色一致性。

### 4. 自变量、因变量、控制变量

#### 自变量

- Council：开 / 关
- token 上限：默认 / 收紧
- 主角参考图：使用 / 跳过
- 图像链路：文本+图像全链路 / 文本优先

#### 因变量

- 单局 LLM 调用次数
- 单局图片调用次数
- 单局 / 单轮时长
- token 消耗
- 兜底率
- 图片缺失率
- 可推进率

#### 控制变量

- 同一主题池
- 同一运行机器
- 同一 provider
- 同一轮数上限
- 同一缓存策略

### 5. 对照组 / 比较组设置

- **对照组 A**：当前默认配置
- **比较组 B**：`EXPERIMENT_NO_COUNCIL=1`
- **比较组 C**：在 B 基础上收紧 `PERF_WORLDVIEW_TOKENS`、`PERF_PLOT_TOKENS_INITIAL`、`PERF_PLOT_TOKENS_NORMAL`
- **比较组 D**：在 B 或 C 基础上启用 `EXPERIMENT_SKIP_PROTAGONIST_REF=1`

建议按逐步消融方式进行，而不是一次改完：

1. A vs B：看 Council 成本
2. B vs C：看 token 上限成本
3. C vs D：看主角参考图链路成本

### 6. 实验对象与运行条件

- 对象：Web 主链路，必要时辅以 `DN-experiment/run_simple_experiment.py`
- 样本量建议：每组 20 到 30 个主题
- 每主题 3 次重复
- 每次跑 3 到 5 轮

### 7. 具体执行步骤

1. 以默认 `.env` 为基线记录一轮结果
2. 设置 `EXPERIMENT_NO_COUNCIL=1` 后重跑同一主题集
3. 调整 `PERF_*` token 参数，重跑同一主题集
4. 设置 `EXPERIMENT_SKIP_PROTAGONIST_REF=1`，重跑同一主题集
5. 每组运行后：
   - 汇总 `provider_events.jsonl`
   - 统计 `DN-experiment/` 中对应局的 scene 产物
6. 抽样人工检查：
   - 剧情是否仍可推进
   - 是否明显空洞或截断
   - 图片是否明显错角色或缺图

### 8. 需要记录的数据

- 配置名
- 是否开启 Council
- token 参数值
- 是否跳过主角参考图
- 单局总时长
- 单局 LLM 调用数
- 单局图片调用数
- 单局 token 消耗
- provider 平均排队 / p95 排队
- 完成局比例
- 可推进轮数
- 兜底文本触发率
- 图片返回率

### 9. 评测指标

- 平均单局时长
- 平均首屏时长
- 平均单轮响应时长
- 平均 LLM 调用数
- 平均图片调用数
- 平均 token 消耗
- provider 平均排队时间
- 失败率 / 超时率
- 兜底率
- 图片返回率
- 人工抽样通过率

### 10. 结果分析方法

1. 先看 **效率收益**
   - 时长下降多少
   - token 降多少
   - 调用次数降多少

2. 再看 **效果代价**
   - 可推进率是否下降
   - 图片缺失率是否上升
   - 兜底率是否上升

3. 输出最终结论时，用“单位效果成本”表达：
   - 例如“关闭 Council 后，首屏时长下降 35%，但剧情抽样质量仅轻微下降，可作为默认实验配置”

### 11. 预期现象

- 关闭 Council 应该是最明显的提速点之一
- 收紧 token 会进一步降低平均时延，但有概率增加文本简化或截断
- 跳过主角参考图会缩短图片链路，但角色一致性可能变差

### 12. 潜在风险与误差来源

- 模型输出随机性导致质量波动
- token 收紧后未必总是更快，若频繁重试反而可能变慢
- 跳过主角参考图对不同题材影响不一致
- 当前图片质量缺少自动量化分数，因此角色一致性主要依赖人工抽样

---

## 实验 3：吞吐与并发稳定性实验

### 1. 实验名称

吞吐与并发稳定性实验

### 2. 实验目的

评估 DN 在多局同时运行时的系统容量，定位瓶颈是在 provider 队列、缓存锁、图片并发还是预生成线程管理。

### 3. 核心假设

1. 随着并发局数提升，provider 队列等待会比纯服务时延增长更快。
2. 高并发下，预生成和缓存锁竞争会增加“文本已生成但缓存未及时命中”的现象。
3. 批处理模式下，吞吐瓶颈主要不在前端，而在 provider 门控和多线程资源争用。

### 4. 自变量、因变量、控制变量

#### 自变量

- 并发局数：1 / 3 / 5 / 10
- 运行模式：Web 单局交互 / 批量主题运行
- provider 优先级策略：默认 / 调低低优先级任务占比

#### 因变量

- 每小时完成局数
- provider 平均排队时间
- provider p95 排队时间
- 平均服务时延
- 失败率 / 超时率 / cancel 率
- 缓存命中率
- 锁等待迹象

#### 控制变量

- 固定主题池
- 固定模型与图像配置
- 固定每局轮数
- 固定 token 参数

### 5. 对照组 / 比较组设置

- **对照组 A**：单并发运行
- **比较组 B**：3 并发
- **比较组 C**：5 并发
- **比较组 D**：10 并发

如时间有限，可先跑 1 / 3 / 5 三档。

### 6. 实验对象与运行条件

- 对象一：Web 主链路并发请求
- 对象二：`DN-experiment/run_batch_themes.py` 的批处理链路
- 每档并发建议至少运行 20 局
- 每局固定 2 到 5 轮

### 7. 具体执行步骤

1. 清理并归档实验前的 provider 日志
2. 先用单并发跑一轮，作为系统容量基线
3. 按 3 / 5 / 10 并发逐步增加压力
4. 每轮实验期间持续收集：
   - provider 事件日志
   - 失败请求
   - 超时请求
   - 兜底返回
5. 每档并发结束后运行：
   - `python scripts/analyze_provider_events.py`
6. 如发现缓存异常，再复核：
   - `server/cache.py`
   - `server/pregeneration.py`
   - 是否出现文本完成但缓存未及时写回

现阶段最容易落地的方式是：

- 批处理：直接使用 `DN-experiment/run_batch_themes.py`
- 服务链路：用多进程或多个终端并行触发 Web API 调用

### 8. 需要记录的数据

- 并发档位
- 完成局数
- 总运行时间
- 单位时间完成局数
- provider 平均排队时间
- provider p95 排队时间
- provider 平均服务时延
- LLM 和图片请求失败率
- 超时率
- 取消率
- 兜底率
- 缓存命中率
- 图片返回率

### 9. 评测指标

- 吞吐量：局 / 小时
- 平均时延、p95 时延
- 平均排队、p95 排队
- 错误率
- 超时率
- 缓存命中率
- 单位结果成本代理

### 10. 结果分析方法

1. 画出并发档位与吞吐量曲线
2. 画出并发档位与 p95 排队时间曲线
3. 识别拐点：
   - 如果吞吐不再上升、但排队急剧上升，则该档位已超过舒适容量
4. 对比 LLM 和图片链路：
   - 是文本先拥塞，还是图片先拥塞
5. 复核缓存与锁：
   - 如果失败率上升但 provider 时延变化不大，则优先查缓存锁和预生成线程协同

### 11. 预期现象

- 低并发时吞吐增长较线性
- 并发升高后，p95 排队时间会快速恶化
- 高并发下，LLM 队列通常比图片队列更先成为主瓶颈
- 缓存与预生成可能在高并发下出现收益下降甚至污染风险

### 12. 潜在风险与误差来源

- 外部 provider 本身的限流策略可能波动
- 网络波动会放大 p95
- 多终端并发不完全等于真实线上流量
- 现有日志已能观测 provider 队列，但对系统资源竞争仍缺少 CPU / 内存采样

---

## 五、实验实施建议与风险提示

### 1. 推荐实施顺序

建议按以下顺序推进，而不是三组一起跑：

1. **先跑实验 1**
   - 先知道玩家在等什么
2. **再跑实验 2**
   - 确定哪种配置最值得作为后续默认实验配置
3. **最后跑实验 3**
   - 用更稳的配置做并发实验，避免把已知低效配置拿去压测

### 2. 推荐的最小可执行版本

如果时间有限，先做下面这个最小版本：

1. 用 `test_speed.py` 跑世界观首屏时长
2. 用 10 个固定主题跑 Web 主链路 5 轮
3. 汇总 `provider_events.jsonl`
4. 对比：
   - 默认配置
   - `EXPERIMENT_NO_COUNCIL=1`
   - 热缓存复跑

仅这一轮，就足以回答：

- 首屏慢主要是不是 Council 导致
- 后续轮次慢主要是不是 provider 排队导致
- 热缓存有没有明显价值

### 3. 建议优先补充的轻量埋点

虽然本版方案可直接执行，但为了让结果更稳定，建议后续补两个轻量埋点：

1. **轮级结构化日志**
   - 每轮记录：
     - game_id
     - round_idx
     - option_idx
     - text_ready_ms
     - image_ready_ms
     - pregen_hit
     - fallback_used

2. **系统资源采样**
   - 每 1 秒记录一次：
     - CPU
     - 内存
     - GPU（若有）

这样可以把“外部 provider 慢”和“本地资源争用慢”区分开来。

### 4. 实验记录规范建议

每次实验建议固定输出四类产物：

1. 原始 provider 日志
2. provider 汇总表
3. 单局实验产物目录
4. 最终结论表

建议最终汇总表按如下字段整理：

- 实验名称
- 配置名
- 主题数
- 总局数
- 平均首屏时长
- 平均单轮文本时长
- 平均单轮图片时长
- LLM 调用数
- 图片调用数
- 平均排队时间
- p95 排队时间
- 完成局比例
- 图片返回率
- 兜底率
- 结论

### 5. 当前最需要警惕的风险

1. **把冷缓存和热缓存混在一起统计**
   - 会让结果失真

2. **只报平均值，不报 p95**
   - 会掩盖严重卡顿

3. **只报效率，不做效果约束**
   - 容易得出没有业务意义的“优化”

4. **多变量同时改动**
   - 难以解释因果

5. **直接用旧日志做新实验结论**
   - provider 日志必须按实验批次归档

### 6. 本版方案的落地结论

基于当前仓库状态，DN 的效率实验已经具备启动条件，不需要先大规模重构代码。最现实、最具价值的路径是：

- 先利用现有日志和脚本做三类实验
- 先识别大瓶颈，再决定是否补埋点
- 把“效率-效果双轴”作为统一结论口径

如果后续要把这套方案进一步升级成长期基准，建议新增一个专用 benchmark harness，但在当前阶段，这不是启动效率实验的前置条件。

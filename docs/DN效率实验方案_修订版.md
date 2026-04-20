一、DN 项目运行机制梳理

先说我认为目前做效率实验前“还缺但不阻塞初版方案”的信息：

缺少统一的性能埋点层。当前项目有实验落盘和大量控制台日志，但没有把 LLM 调用耗时 / token / 重试 / 图像生成耗时 / CPU / GPU / 内存 / 缓存命中 统一记录到一份结构化日志里。
缺少固定的“质量下限”定义。文本侧目前更偏流程可跑通，图像侧已有一些评估脚本，但还没有把“效率不能以明显伤害效果为代价”量化成统一门槛。
缺少一个不改业务逻辑、专门跑效率基准的 benchmark harness。现有 DN-experiment 和 DN-experiment-2.0 已经很接近，但还不是完整的性能测量器。
基于合理假设，我下面的方案默认：

使用 C:\Users\zhang\Desktop\DN\game_themes_100.json 作为固定主题集。
使用 C:\Users\zhang\Desktop\DN\DN-experiment-2.0\run_text_segments_test.py 的“多段连续剧情”思路作为基准主线。
允许为后续实验补一个很薄的 telemetry wrapper，但不大改核心生成逻辑。
1. 整体架构

DN 本质上是一个“LLM 驱动的互动叙事游戏 + 图像生成系统”，其结构是：

入口层
CLI 入口：C:\Users\zhang\Desktop\DN\main.py
Web 入口：C:\Users\zhang\Desktop\DN\game_server.py
生产启动脚本：C:\Users\zhang\Desktop\DN\start_server.py:11
聚合层
C:\Users\zhang\Desktop\DN\main2.py 主要是旧式聚合入口，负责把 src/ 中拆分后的能力重新暴露出来，供 CLI/Web 共用
核心逻辑层 src/
llm/：世界观与剧情生成
story/：单选项剧情推进、批量选项生成、结局
image/：场景图/主角图生成、提示词优化、缓存、存储
characters/：角色档案、配角检测、参考图裁剪
worldview/：模板、缓存、解析
game/：CLI 的主循环
wiki/：外部题材信息查找
Web 服务辅助层 server/
预生成缓存、锁、SSE 事件、实验落盘、目录配置
可以概括成：

前端/CLI -> game_server.py / TextAdventureGame -> main2.py 聚合 -> src.llm / src.story / src.image / src.characters -> 外部 LLM/图像 API + 本地缓存/存档

2. 核心模块及职责

世界观生成
C:\Users\zhang\Desktop\DN\src\llm\global_gen.py:35
负责根据主题、难度、基调、主角属性生成 global_state
内含“分阶段世界观生成”“单模型/群体智能 Council 切换”“token 上限控制”
Council 群体智能
C:\Users\zhang\Desktop\DN\src\llm\council_core.py
典型三阶段：
多模型并行生成
多模型匿名互评排序
主席模型综合
这是明显的高成本、高时延链路
单轮剧情/选项推进
C:\Users\zhang\Desktop\DN\src\story\options.py:130
_generate_single_option 负责“执行某个选项 -> 生成新场景 -> 生成下一层两个选项 -> 可选生成场景图”
generate_all_options 在 C:\Users\zhang\Desktop\DN\src\story\options.py:1667，负责批量生成多个选项对应内容
图像生成链路
C:\Users\zhang\Desktop\DN\src\image\api_providers.py:975
generate_scene_image 支持本地缓存、提示词缓存、参考图、多 provider、重试、下载落盘
Web 预生成与缓存
C:\Users\zhang\Desktop\DN\game_server.py:507 /generate-option
C:\Users\zhang\Desktop\DN\game_server.py:1205 /pregenerate-next-layers
C:\Users\zhang\Desktop\DN\server\pregeneration.py
核心目的是把用户“读当前剧情”的时间拿来预生成下一层内容，降低交互等待
实验落盘
C:\Users\zhang\Desktop\DN\server\experiment_log.py
C:\Users\zhang\Desktop\DN\DN-experiment\experiment_save.py
将剧情段、prompt、图像路径等落盘到实验目录
3. 游戏运行主流程

Web 模式主流程最典型：

启动服务：python game_server.py 或 python start_server.py
前端提交主题/难度/基调等到 /generate-worldview
后端调用 llm_generate_global(...) 生成世界观与初始状态
系统生成初始剧情/初始选项
用户点击一个选项，前端请求 /generate-option
后端优先查预生成缓存；命中则直接返回，未命中则现场生成
返回新场景、下一组选项、可选场景图
前端继续触发 /pregenerate-next-layers 做后台预生成
达到章节条件后，可触发 /generate-ending
CLI 模式则由 TextAdventureGame 驱动，逻辑相似，只是交互界面换成终端。

4. 数据流与调用链

最重要的数据对象是 global_state，其中至少包含：

core_worldview：世界观、角色、章节、主线
flow_worldline：当前章节、主线进度、角色状态、是否解锁深层背景等
运行时附加字段：game_id、视觉上下文、缓存提示等
关键调用链：

世界观链
用户配置 -> llm_generate_global -> global_state
单轮剧情链
global_state + selected_option -> _generate_single_option -> scene + next_options + flow_update + scene_image
图像链
scene -> prompt 优化 -> provider API -> 本地缓存/云存储 -> URL 回填 option_data
Web 预生成链
当前场景 -> generate_all_options(..., skip_images=...) -> 缓存 layer1/layer2 -> 用户选择时直接取
5. 启动方式、配置方式、实验入口

启动方式：

Web：
C:\Users\zhang\Desktop\DN\start_server.py:11
默认 0.0.0.0:5001
CLI：
python main.py
或 python main2.py
一键脚本：
C:\Users\zhang\Desktop\DN\启动游戏.bat
C:\Users\zhang\Desktop\DN\启动游戏.sh
配置方式：

主配置来自 .env
关键配置定义在 C:\Users\zhang\Desktop\DN\src\config.py
性能相关开关集中在 C:\Users\zhang\Desktop\DN\src\constants.py
PERF_WORLDVIEW_TOKENS
PERF_PLOT_TOKENS_INITIAL
PERF_PLOT_TOKENS_NORMAL
PERF_STAGED_WORLDVIEW
PERF_ASYNC_PREGEN
PERF_STREAM_FIRST
PERF_OPT_RETRY
实验入口：

单段最小实验：
C:\Users\zhang\Desktop\DN\DN-experiment\run_simple_experiment.py
批量主题、两段剧情实验：
C:\Users\zhang\Desktop\DN\DN-experiment\run_batch_themes.py
多段连续剧情实验：
C:\Users\zhang\Desktop\DN\DN-experiment-2.0\run_text_segments_test.py
基于实验 JSON 的后补生图：
C:\Users\zhang\Desktop\DN\DN-experiment-2.0\generate_images_from_experiment_json.py
这里非常关键的一点是：现有实验脚本已经在主动绕开某些高耗时环节，比如设置 EXPERIMENT_NO_COUNCIL=1、_skip_protagonist_reference=True。这说明项目作者已经隐含地把“Council”和“主角参考图链路”视为主要效率瓶颈。

6. 可能影响效率表现的关键环节

我按影响优先级排序：

Council 三阶段生成
世界观完整版默认可能走多模型并行 + 互评 + 主席综合
直接放大 LLM 调用次数、token、总时长、失败重试概率
见 C:\Users\zhang\Desktop\DN\src\llm\global_gen.py:204 与 C:\Users\zhang\Desktop\DN\src\llm\council_core.py
单轮剧情 prompt 很重
_generate_single_option prompt 非常长，且要求大量结构化字段
会推高输入 token、输出 token、解析失败重试、长尾延迟
场景图生成链较长
prompt 优化 -> provider 请求 -> 轮询/下载 -> 本地缓存写入
若带参考图/上一场景上下文，会继续增重
预生成两层内容
优点：降低用户感知延迟
代价：带来额外 speculative work，可能生成了没被选的分支
因此必须测“命中率”和“浪费率”，不能只看前台快不快
锁与缓存竞争
pregeneration_cache + cache_lock
高并发时可能出现等待、锁持有时间过长、缓存污染
图像与实验落盘 I/O
image_cache/、DN-experiment/ 的文件写入会引入磁盘波动
请求等待机制
/generate-option 明确有等待事件与较长超时，长尾很可能来自“等预生成完成”而非纯推理
重试与 provider 不稳定
src/llm/api.py 和 src/image/api_providers.py 都有 timeout / retry / 429 处理
这类失败在平均值里常被掩盖，但对 p95/p99 极其敏感
7. 当前存在的多种运行模式/配置分支

至少有这几类要区分：

CLI vs Web
CLI 更直接，Web 多了 HTTP、前端状态、SSE、预生成
单模型 vs Council
EXPERIMENT_NO_COUNCIL=1 会显著改变成本结构
世界观生成模式
staged worldview / full worldview
文本-only vs 文图联合
DN-experiment-2.0 支持先纯文本跑，再补图
冷缓存 vs 热缓存
世界观缓存、prompt 缓存、image cache、预生成缓存都可能改变结果
带主角参考图 vs 跳过主角参考图
现有实验脚本已默认跳过，说明其对效率影响明显
二、相关实验方法调研总结

我没有堆文献，而是提炼了最适合 DN 借鉴的几类做法。

1. 可借鉴的共通原则

不只看平均耗时，要同时看分位数
LLM/交互系统常见问题不是 mean，而是 p95/p99 尾延迟
不只看端到端，要同时做分阶段剖析
至少拆成：世界观生成、单轮剧情生成、图片生成、缓存等待、I/O 落盘
不只看速度，要给质量设下限
否则“缩 prompt / 关模块 / 降 token”很容易得到假优化
不只看成功率，要看达到成功的代价
对交互式/智能体系统，success per cost、success per step、success per second 比单独 success 更有信息量
必须区分冷启动与热启动
首次生成和缓存命中后的表现往往是两种系统
必须区分单用户与并发用户
单局快不代表系统吞吐高；并发下锁竞争、排队等待、provider 限流都会暴露
2. 来自 LLM 服务/推理系统的借鉴点

借鉴点一：把指标分成“请求级”和“服务级”。

vLLM 文档明确把指标分成 server-level 与 request-level，两类指标要配套看：vLLM Metrics
对 DN 很适合映射成：
请求级：单次 generate-worldview / generate-option / generate-scene-image 的时延、token、重试
服务级：当前并发数、等待数、缓存使用率、吞吐
借鉴点二：使用 TTFT / TPOT / E2E 三层时延。

vLLM 直接暴露 time_to_first_token_seconds、inter_token_latency_seconds、e2e_request_latency_seconds：vLLM Metrics
MLPerf 也把 LLM 服务场景的约束写成 TTFT 和 TPOT：MLPerf Inference Docs
对 DN 的映射：
TTFT：从发起请求到后端拿到首个有效剧情片段/首个可展示结果
TPOT：如果后续做流式输出，可记录每 token 或每 chunk 间隔
E2E：用户点击选项到前端完整渲染完新剧情/新图片的总时长
借鉴点三：关注缓存与排队，而不只看模型本身。

OpenAI 官方 latency guide 强调：少请求、并行化、共享 prompt 前缀、利用缓存都很关键：OpenAI Latency Optimization
DN 中最对应的是：
共享 prefix / prompt caching
预生成
image cache
减少串行请求数
3. 来自交互式智能体/多轮决策系统的借鉴点

借鉴点一：把“步数/轮数”当作一等公民指标。

WebArena 的核心是端到端任务成功率，但它的意义在于：长链路、多步任务更接近 DN 这种交互式叙事系统，而不是单次问答：WebArena paper
对 DN 来说，步数/轮数至少要测：
单局完成到章节结束需要多少轮
单轮平均耗时
成功推进一章所需的累计 token / 成本 / 时间
借鉴点二：效果评估要看“任务完成”，效率评估要看“完成代价”。

WebArena 说明只看成功率不够，因为复杂长任务里，成功背后的步骤数和资源消耗差异很大
DN 应当形成类似：
章节推进成功率
平均推进轮数
单位推进成本
单位成功成本
4. 来自游戏性能分析的借鉴点

借鉴点一：用 timeline 观察跨线程相关性。

Unity Profiler 强调 Timeline view 的价值在于“所有线程放在同一时间轴上看相关性”，而不是只看总表：Unity CPU Profiler
对 DN 非常适合：
主请求线程
预生成线程
图像生成线程
文件写入线程/外部下载
这样才能区分：
是 LLM 慢
还是锁阻塞
还是 I/O 慢
还是图像下载回填慢
借鉴点二：跟踪内存分配与 GC/对象增长。

Unity 文档明确建议关注 GC Alloc，频繁分配会带来后续性能问题：Unity CPU Profiler
DN 虽然不是 Unity，但同理：
预生成缓存、场景 JSON、图片对象、prompt cache 都可能推高内存与回收压力
因此要记录 RSS、峰值内存、缓存大小、磁盘增长速度
5. 对 DN 最值得直接照搬的方法

我建议直接借鉴以下 6 点：

指标分层：请求级 + 系统级
时延分层：TTFT + 单轮耗时 + E2E
结果分层：效率指标 + 效果指标联合汇报
工况分层：冷缓存/热缓存，单用户/并发
结构分层：文本链路 / 图像链路 / 预生成链路拆开测
统计分层：mean + median + p95，且做 paired comparison
三、效率实验总体设计思路

1. 总体目标

不是简单回答“DN 快不快”，而是回答 3 个更有价值的问题：

DN 的主要时间花在哪个链路？
哪些优化能明显提升响应效率，同时不明显伤害效果？
在真实 Web 交互场景下，预生成/缓存到底是净收益还是净浪费？
2. 统一实验对象

建议固定三类对象：

主题集
从 C:\Users\zhang\Desktop\DN\game_themes_100.json 中选 30 个主题
分层抽样：写实/幻想/悬疑/校园等都覆盖
局内长度
短链：2 段
中链：5 段
长链：10 段
运行模式
文本-only
文图联合
Web 交互
3. 统一指标体系

建议所有实验统一记录：

时间
单局总时长
世界观生成时长
单轮剧情生成时长
单图生成时长
首响应时延 TTFT
p50 / p90 / p95 / max
调用
LLM 调用次数
图像调用次数
重试次数
失败次数
资源
CPU 平均/峰值
内存平均/峰值 RSS
GPU 利用率与显存峰值（若本机用到）
磁盘写入量
成本
input tokens / output tokens
单局 token 消耗
单轮 token 消耗
单位章节推进成本
系统行为
预生成命中率
预生成浪费率
图片缓存命中率
世界观缓存命中率
并发等待长度/锁等待时间
效果
章节推进成功率
剧情完整率
选项可用率
图像质量/一致性分数
人工小样本偏好
4. 建议的统一日志格式

每次请求/步骤输出一条 JSONL：

run_id
theme_id
mode
stage (worldview / option_text / scene_image / ending)
start_ts
end_ts
latency_ms
llm_model
image_provider
input_tokens
output_tokens
retry_count
cache_hit
pregen_hit
cpu_avg
mem_peak_mb
gpu_util_avg
success
quality_flags
这样后面三组实验能共用一套采样与报表。

四、3 组效率实验详细方案

实验 1：文本主链推理效率实验

实验名称
文本主链推理效率-效果权衡实验
实验目的
找出 DN 在“世界观生成 + 多轮剧情推进”上的主要效率瓶颈，并确定单模型、Council、token 预算之间的性价比最优点
核心假设
H1：Council 会显著提高世界观生成时长、token 消耗和单局总成本
H2：适度压缩 worldview_max_tokens / plot_max_tokens 可明显降耗，但效果下降未必显著
H3：对 DN 这类长链路系统，减少一次大请求比微调 prompt 长度更有效
自变量
生成模式：
Baseline：默认配置，世界观允许 Council
单模型：EXPERIMENT_NO_COUNCIL=1
单模型 + 降 token 预算：下调 PERF_WORLDVIEW_TOKENS、PERF_PLOT_TOKENS_INITIAL、PERF_PLOT_TOKENS_NORMAL
局长：2 段 / 5 段 / 10 段
因变量
单局总时长
世界观生成时长
单轮平均耗时
LLM 调用次数
input/output tokens
单局总 token
单位有效剧情段成本
章节推进成功率
剧情结构完整率
控制变量
相同主题集
相同温度、难度、基调
文本-only，关闭场景图生成
相同机器、相同网络时段
对照组/比较组设置
对照组：默认配置
比较组 A：关闭 Council
比较组 B：关闭 Council + 降 token
实验对象与运行条件
30 个主题
每个主题每组跑 3 次
共 30 x 3 x 3 = 270 局
建议优先用轻量 benchmark harness 直接调 llm_generate_global 与 _generate_single_option_text_only
具体执行步骤
固定主题清单
为每组配置单独环境变量
每局生成世界观后，固定总是选第一个选项，连续推进 10 段
每段记录时延/token/调用次数
每局结束后写入一条汇总记录
需要记录的数据
T_worldview
T_segment_i
tokens_worldview_in/out
tokens_segment_i_in/out
llm_calls_total
retries_total
scene_parse_failures
chapter_progress_success
评测指标
Avg game duration
p95 segment latency
Avg tokens per segment
Cost per completed segment
Success rate
Success per 1k tokens
结果分析方法
对同一主题做 paired comparison
汇报 mean/median/p95
画 Pareto 图：横轴总时长，纵轴效果分
统计显著性可用 Wilcoxon signed-rank 或 bootstrap CI
预期现象
Council 组世界观时长和 token 显著更高
单模型组单局更稳定，长尾更短
降 token 组平均耗时明显下降，但在复杂主题上可能出现剧情信息不足
潜在风险与误差来源
外部 API 波动
provider 侧速率限制
文本-only 与真实 Web 体验有差距
若没有真实 usage 返回，token 可能需要估算
实验 2：交互响应-预生成-缓存实验

实验名称
Web 交互响应与预生成收益实验
实验目的
衡量 pregeneration_cache、两层预生成与缓存命中对用户响应延迟和系统资源占用的净收益
核心假设
H1：预生成能显著降低“用户点击选项后的等待时间”
H2：预生成在低命中率主题上会产生高浪费率
H3：并发提高后，锁竞争和等待会抵消预生成收益
自变量
预生成策略：
关闭预生成
开启 layer1 预生成
开启 layer1+layer2 预生成
缓存状态：冷缓存 / 热缓存
并发等级：1 / 5 / 10 用户
因变量
用户点击后到返回剧情的延迟
首屏响应延迟
预生成命中率
预生成浪费率
吞吐量（req/min）
锁等待时间
内存峰值
CPU 峰值
控制变量
相同主题、相同前端流程
相同图像策略（建议先 text-only 或固定图像开关）
相同机器与网络
对照组/比较组设置
对照组：关闭 /pregenerate-next-layers
比较组 A：仅一层预生成
比较组 B：两层预生成
实验对象与运行条件
使用 Web 服务 C:\Users\zhang\Desktop\DN\game_server.py
通过本地 HTTP harness 或 auto_play.py 的简化版自动交互
每组 20 个主题，每主题 5 次
具体执行步骤
启动 Web 服务
模拟前端请求序列：
/generate-worldview
获取初始剧情
点击选项请求 /generate-option
按配置触发或不触发 /pregenerate-next-layers
连续推进若干轮
对并发组同时发起多局
每次记录“用户可感知等待时间”和后台预生成事件
需要记录的数据
T_click_to_response
T_worldview_to_first_playable
pregen_hit
pregen_generated_count
pregen_used_count
wasted_pregen_count
cache_entry_size
lock_wait_ms
num_requests_running/waiting（可自定义）
评测指标
Median click latency
p95 click latency
Playable throughput
Pregeneration hit rate
Pregeneration waste rate = unused generated branches / all generated branches
Memory per active session
结果分析方法
分冷/热缓存分别画图
分单用户/并发分别汇报
比较“用户等待缩短多少”与“额外资源消耗增加多少”
形成 ROI 指标：saved_user_wait_ms / extra_cpu_sec
预期现象
单用户下，一层预生成收益最大
两层预生成会进一步缩短个别点击等待，但浪费率也会上升
10 并发下，锁与等待事件会明显拉高尾延迟
潜在风险与误差来源
自动化脚本与真实用户阅读停顿不同，会影响预生成窗口
网络 API 抖动可能掩盖缓存收益
如果不开结构化埋点，锁等待时间不易准确分离
实验 3：图像链路效率-效果联合实验

实验名称
场景图生成链路效率与一致性实验
实验目的
分析图像生成链路中“主角参考图、上下文参考、prompt 优化、缓存”各因素对时延、资源与效果的影响
核心假设
H1：跳过主角参考图会显著降低图像链路耗时
H2：热缓存能大幅降低重复场景的图像成本
H3：去掉参考链路虽更快，但角色一致性和视觉连续性会下降
自变量
图像策略：
全量链路：prompt 优化 + 主角参考 + 连续场景视觉上下文
跳过主角参考：_skip_protagonist_reference=True
热缓存复用：同一批 scene 二次生成
文本来源：
直接在线文图联动
使用 DN-experiment-2.0 已落盘 scene 再离线补图
因变量
单图生成耗时
图像 provider 调用次数
图片缓存命中率
下载/落盘时间
图像质量分
角色一致性分
单图成本
控制变量
相同 scene 文本
相同 image_style
相同 provider
相同分辨率与 timeout
对照组/比较组设置
对照组：全量链路
比较组 A：跳过主角参考
比较组 B：热缓存复用
实验对象与运行条件
先用 C:\Users\zhang\Desktop\DN\DN-experiment-2.0\run_text_segments_test.py --segments 10 --text-only 生成固定文本样本
再用 C:\Users\zhang\Desktop\DN\DN-experiment-2.0\generate_images_from_experiment_json.py 补图
建议 15 个主题 x 10 段 = 150 个 scene
具体执行步骤
生成固定的 scene JSON 数据集
对同一批 scene 分别跑 3 个图像策略
每张图记录开始/结束时间、重试、缓存命中、文件大小
跑已有图像评估脚本，如 scripts/eval_clip_score.py、DN-experiment/eval_character_consistency.py
需要记录的数据
T_image_total
T_prompt_opt
T_provider_call
T_download_cache_write
image_retry_count
cache_hit
file_size_kb
clip_score
character_consistency_score
评测指标
Avg image latency
p95 image latency
Image cache hit rate
Images/min
Cost per valid image
CLIP score
Character consistency
Quality per second
结果分析方法
用同一 scene 做 paired 对比
画效率-效果散点图
设质量底线后，寻找最快可接受配置
预期现象
跳过主角参考组最快
热缓存组时延最低
全量链路在一致性上最好，但吞吐最低
潜在风险与误差来源
图像质量受 provider 波动影响大
CLIP 分数不完全等于“玩家觉得好”
scene 文本本身差异也会影响图像难度
五、实验实施建议与风险提示

1. 我建议的落地顺序

第一步：先做实验 1
因为它最容易隔离文本主链成本，最快帮你确定“Council 值不值得”
第二步：再做实验 2
因为 Web 交互体验是否快，核心取决于预生成到底有没有净收益
第三步：最后做实验 3
因为图像链路最不稳定，适合在文本链路已相对稳定后单独分析
2. 最值得优先埋点的位置

C:\Users\zhang\Desktop\DN\src\llm\api.py
记录每次 LLM 请求时延、重试、usage
C:\Users\zhang\Desktop\DN\src\llm\global_gen.py:35
记录世界观生成分阶段耗时
C:\Users\zhang\Desktop\DN\src\story\options.py:130
记录单选项剧情生成耗时、解析失败、是否触发生图
C:\Users\zhang\Desktop\DN\src\image\api_providers.py:975
记录 prompt 优化、provider 请求、下载缓存、命中情况
C:\Users\zhang\Desktop\DN\game_server.py:507
记录 /generate-option 请求总耗时、等待事件耗时、缓存命中
C:\Users\zhang\Desktop\DN\server\pregeneration.py
记录预生成开始/结束、分支命中/浪费
3. 结果汇报建议

最终报表不要只放平均值，至少要有：

一张总表：3 个实验、各组 mean/median/p95
一张 Pareto 图：效率 vs 效果
一张 waterfall/stack 图：总耗时分解
一张缓存收益图：冷/热缓存差异
一张并发表：1/5/10 并发下吞吐与尾延迟
4. 关键风险提示

如果不设质量下限，实验会天然偏向“关模块”
如果不区分冷/热缓存，结论会失真
如果只跑 1-2 个主题，结论会高度偶然
如果只看均值，不看 p95，会低估真实用户痛点
如果不做 paired comparison，同一主题复杂度差异会污染结果
5. 这版方案最贴合 DN 项目的原因

它直接围绕 DN 现有的三条真实链路：文本生成、Web 预生成、图像生成
它复用了你仓库里已经存在的实验入口与目录结构，而不是另起炉灶
它把 DN 代码里已经暴露出来的性能分支，变成了可比较的自变量
它不是泛泛谈“模型推理效率”，而是可以直接指导你下一步怎么跑
借鉴来源（方法论）

OpenAI Latency Optimization: https://developers.openai.com/api/docs/guides/latency-optimization
vLLM Metrics: https://docs.vllm.ai/en/stable/design/metrics/
MLPerf Inference Docs: https://docs.mlcommons.org/inference/
WebArena paper: https://arxiv.org/abs/2307.13854
Unity CPU Profiler: https://docs.unity.cn/2023.1/Documentation/Manual/ProfilerCPU.html

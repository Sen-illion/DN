# 实验章节中文总稿（2026-04-26）

## 4. 实验设计与结果分析

### 4.1 实验目标与整体思路

本文实验部分的目标可以概括为三个层面。首先，我们希望验证 DN 是否已经形成一个稳定、可复现且能够完整跑通的端到端系统，而不是若干模块的功能拼接。其次，我们希望通过引入可执行的外部 baseline，说明 DN 的表现并非只在自建评测中成立，而是在可比任务条件下相对于代表性开源系统仍具有研究意义。最后，我们希望通过消融实验说明 DN 当前配置并非经验性堆叠，而是由若干关键模块共同塑造出来的系统行为。

基于这一目标，本文将实验组织为三部分。第一部分是 DN 完整系统在原生 benchmark 上的主结果，用于回答“DN 能否稳定完成完整任务流程”；第二部分是外部 baseline 比较，用于回答“DN 在统一 playable-latency 口径下与外部专门系统相比处于什么位置”；第三部分是消融实验，用于回答“DN 当前方法中的关键模块分别发挥了什么作用”。

需要说明的是，当前可直接执行的外部 baseline 主要集中在文本与互动响应侧，而非完整多模态同构系统。因此，本轮主实验采用“DN 完整系统结果 + 可运行外部 baseline + 关键模块消融”的结构，而不再追求一张表面上完全统一、但比较口径混乱的大而全总表。

### 4.2 数据集、协议与评测设置

本轮主实验统一使用 DN 项目现有的 `DN-quality-benchmark-v1` 作为任务来源。该 benchmark 覆盖多种题材、世界设定和叙事压力条件，可以同时支持 DN 原生任务链路与外部 baseline 的适配评测。

对于 DN 原生实验，我们沿用已经完成的 `worldview_default_20` 与 `fullchain_default_20` 结果，用于刻画结构化世界观生成能力与完整系统流程表现。对于外部 baseline，我们另外构建了统一的 playable-latency protocol，并将比较问题固定为：

- 从玩家触发一次交互开始，到系统返回第一份可继续游玩的内容，需要多久？
- 在后续一轮玩家动作后，系统再次返回可继续游玩内容，需要多久？

因此，本轮主实验的核心指标固定为：

- `first_playable_time_s`
- `next_turn_time_s`
- `success_rate`
- `p95_latency_s`

辅助指标包括：

- `playable_output_completeness`
- `interaction_continuity`

需要特别指出的是，我们不再将 `end_to_end_boot_time_s` 或“从零生成全部世界观、角色与资源后的冷启动完整时间”作为本轮主指标，因为这会模糊当前主实验真正要回答的交互等待问题。

在 baseline 侧，当前冻结版核心主表包含四行系统：

1. `DN`
2. `LIGHT`
3. `Plan-Write-Revise`
4. `GenAgents`

其中：

- `LIGHT` 作为当前最具权威性的外部互动对话 / 游戏世界候选 baseline；
- `Plan-Write-Revise` 作为轻量文本即时生成的速度参考 baseline；
- `GenAgents` 作为多轮状态连续性与下一轮交互稳定性的补充 baseline。

另外，`WorldGeneration` 仍被保留，但由于当前机器上可运行的是 fallback reconstruction path，而非完整原论文 pipeline，因此已被固定为补充比较表，而不再放入核心主表。

关于 DN 行的口径，还需要额外说明：当前主表使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy。该定义成立于 DN 的预生成设置下，适合用于当前统一 playable-latency 比较，但不等于“从零冷启动到全部资源完全就绪”的总时长。

### 4.3 DN 原生主系统结果

从原生 benchmark 结果看，DN 在当前版本上已经表现出较强的端到端稳定性。在 `benchmark_v1_worldview_default_20` 中，DN 的 worldview 生成成功数达到 `20/20`，平均延迟为 `33.657 s`，`p95` 延迟为 `68.872 s`。在更完整的 `benchmark_v1_fullchain_default_20` 中，DN 的 fullchain 成功数同样达到 `20/20`，说明当前系统并非只在局部模块上可运行，而是能够从世界观组织、选项生成到主角色结果产出完成整条任务链路。

进一步看分阶段性能，DN 在 fullchain 默认配置下的 worldview 阶段平均耗时为 `12.458 s`，选项生成阶段平均耗时为 `7.662 s`，主角色完成阶段平均耗时为 `55.912 s`。这表明 DN 的主要时间成本集中在后段内容补全与完整互动资源生成，而不在最前面的世界观搭建。换言之，DN 的延迟结构并非均匀分布，而是体现出“前段规划相对稳定、后段完整呈现更重”的特征。

在有效性与可靠性护栏方面，DN 当前也已经具备较完整的支撑证据。现有 summary 显示，worldview success rate、first scene success rate、image return rate、main character completion rate 以及 option count >= 2 rate 均达到 `1.0`；同时 fallback trigger rate、scene prompt pollution rate 以及 protagonist garbled / pollution rate 均为 `0.0`。这些结果说明 DN 不仅能跑完整流程，而且输出在格式、污染控制与基础可用性层面也达到较高稳定度。因此，本文可以较安全地将 DN 描述为一个稳定的完整系统，而不是仅能在个别样本上演示效果的研究原型。

### 4.4 主实验：外部 baseline 比较

本轮主实验主表采用统一 playable-latency protocol，将 DN 与三个已经真正跑通的外部专门系统进行比较。需要强调的是，这一比较并不意味着所有 baseline 与 DN 在系统形态上完全同构。更准确地说，主表中的每一行代表不同类型的外部参照：

- `LIGHT`：权威 external row
- `Plan-Write-Revise`：speed/reference row
- `GenAgents`：continuity supplement row

在当前冻结主表中，DN 的 `first_playable_time_s` 以 `generate_option` 阶段时延作为工作 proxy，数值为 `7.662 s`。与此同时，轻量文本类 baseline 在首轮文本响应上明显更快：`LIGHT` 的 `first_playable_time_s` 为 `0.41 s`，`Plan-Write-Revise` 为 `0.833 s`。这意味着，当前结果并不支持“DN 在所有外部系统中绝对最快”这一表述。

但这并不意味着 DN 在主实验中失败。相反，这组结果更适合支持一个更准确的判断：DN 的输出不应被理解为“任意一句即时文本回复”，而应被理解为“完整系统链路下返回的可继续游玩的互动内容”。换言之，LIGHT 与 PWR 之所以更快，主要说明轻量文本或互动对话模型在单模型条件下生成短文本时具有天然速度优势；而 DN 的结果则反映了一个完整互动叙事系统在保持结构化可玩输出前提下的响应延迟。

与强调 agent 状态连续性的 `GenAgents` 相比，DN 的当前交互延迟并不处于明显劣势。`GenAgents` 的 `first_playable_time_s` 为 `9.76 s`，`next_turn_time_s` 为 `6.285 s`，说明即便是以多轮状态延续为核心的外部系统，也未必在主实验口径下全面优于 DN。因此，`GenAgents` 更适合作为“状态连续性与多轮交互稳定性”的补充对照，而不是 DN 的完整系统替代物。

综合来看，当前主表最稳妥的结论不是“DN 绝对最快”，而是：在完整互动叙事系统链路下，DN 能够以稳定方式返回结构化的可玩内容；而外部 baseline 则分别从权威互动对话、轻量文本生成与多轮状态连续性三个不同方向，构成了对 DN 的参照坐标系。

### 4.5 为什么 LIGHT 进入主表，而 WorldGeneration 转入补充表

`WorldGeneration` 在任务形态上具有一定相关性，因为它比 `LIGHT` 更接近“世界构造型”系统。然而，在当前机器与当前复现路径下，真正跑通的是基于官方 binary story 资产的 fallback reconstruction path，而非原论文所描述的完整 Evennia world pipeline。也就是说，它虽然提供了可运行结果，但该结果在复现忠实度与权威性上弱于一个可直接加载官方 checkpoint 的互动系统。

相比之下，`LIGHT` 具有更强的项目权威性、更明确的互动世界背景，也更容易向审稿人解释其作为主表 external row 的合理性。尽管当前实际跑通的是其公开 checkpoint 的 text-side 可运行切片，而非完整在线世界服务，但它依然比当前 `WorldGeneration` fallback 更适合承担“优先权威外部 baseline”的角色。

因此，本文当前冻结的表述方式是：

- `LIGHT` 保留在主表中；
- `WorldGeneration` 保留在补充比较中；
- 正文中明确说明二者角色不同，避免将它们误写为完全等价的外部竞争系统。

### 4.6 消融实验

为了说明 DN 当前配置的合理性，本文进一步引入了 pregeneration、council 与 readwait 三组消融结果。它们的作用不是简单展示“去掉模块会变差”，而是解释 DN 当前系统行为与性能分布背后的机制来源。

首先，`pregeneration` 消融结果显示其对 worldview 延迟分布有显著影响。在清洗后的 12 样本结果上，`pregen_off_clean12` 的 worldview 平均延迟为 `73.377 s`，而 `pregen_on_clean12` 降至 `16.566 s`。这说明 pregeneration 不是无关紧要的工程优化，而是当前系统能够维持前段响应速度的重要组成部分。

其次，`council` 消融结果表明其并非装饰性模块。在 fullchain 对比中，默认配置保持 `20/20` 成功，而 no-council 配置下降到 `19/20`；同时 worldview 平均延迟由 `12.458 s` 上升到 `16.547 s`。这意味着 council 不仅影响系统的组织效率，也影响一定程度的可靠性，因此可以被视为 DN 方法中的关键支持模块。

最后，`readwait` 消融结果揭示了调度策略对真实场景命中的影响。在清洗后的 `70s` 对比点上，readwait-off 的 real-scene rate 为 `0.0`，而 readwait-on 提升至 `0.5`。虽然 second-click 平均延迟在两种配置之间并未出现数量级差异，但是否保留足够的读取窗口，显著影响了真实场景结果的出现概率。这说明 readwait 不是简单的等待参数，而是与系统最终输出质量直接相关的调度设计。

综合来看，这三组消融共同支持一个核心结论：DN 当前主配置不是随意组合出来的，而是由一组对延迟、稳定性与输出质量均有明确贡献的模块共同构成。

### 4.7 局限性与有效性威胁

尽管本文已经补上了一组可执行的外部 baseline，但这些 baseline 与 DN 并不是严格同构的一对一系统。`Plan-Write-Revise` 更像按需故事生成器，`LIGHT` 更像权威互动对话系统，`GenAgents` 更像状态持续型 agent 系统，因此主表更适合解释为“多类外部参照下的统一 playable-latency 比较”，而不是“同构系统之间的单一胜负表”。

另外，DN 行当前仍使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy。这一做法在当前主实验中是合理的，但它并不等于“从零冷启动到全部资源完全就绪”的总时长，因此不能被夸大解释为更强的全链路启动结论。

`LIGHT` 的权威性强于其语义贴合度。它之所以进入主表，主要因为其公开代码、公开 checkpoint 和互动叙事背景都更具对外说明力；但在当前 protocol 下，它的输出仍偏向短对话式响应，而不是与 DN 完全同构的中文互动叙事内容。因此，本文应将其解释为“权威 external latency/reference row”，而不是与 DN 完全等价的语义对手。

`WorldGeneration` 虽然在任务形态上更接近世界构造型系统，但当前周期内可运行的是 fallback reconstruction path，而不是完整原始 pipeline，因此只能保留在补充比较表中，而不宜继续放在核心主表中承担主要结论压力。

此外，本轮主实验的中心问题被固定为点击后到可玩内容返回的等待效率，因此它并不直接回答图像质量、世界观丰富度、叙事文学性或角色塑造细腻度等全维度质量问题。当前机器条件下，`StoryDiffusion` 等视觉 baseline 也尚未形成稳定、批量、可复现的正式结果，这意味着 DN 在图文协同完整系统层面的外部对照仍不充分。

最后，baseline 适配层本身会引入工程偏置。为了让外部系统进入统一 benchmark，我们为其增加了 playable adapter、状态包装和统一结果协议。本文已尽量保证这些适配不替换 baseline 的核心生成机制，但仍应承认：当前结论更准确的含义是“baseline 核心机制在统一 playable wrapper 下的表现”，而不是完全无干预条件下的原始论文 demo 表现。

### 4.8 小结

综合主系统结果、外部 baseline 对比与消融实验，可以得到当前最安全也最有说服力的结论。第一，DN 已经是一个在自建 benchmark 上稳定、可复现、能够完整跑通流程的端到端系统。第二，DN 并非只在自家协议下表现良好；在统一 playable-latency protocol 下，DN 已经与多个外部专门系统完成对照，其中 `LIGHT` 提供了最具权威性的主表外部参照，`Plan-Write-Revise` 提供了轻量文本速度参考，`GenAgents` 提供了连续性交互补充对照，而 `WorldGeneration` 则以补充表形式保留。第三，DN 当前配置具备明确的机制支撑：pregeneration、council 与 readwait 三个模块都对系统延迟、可靠性或输出行为产生了实质影响。

因此，当前实验章节最合适的整体表述应当是：DN 已具备较强的完整系统能力，并在统一 playable-latency protocol 下形成了可执行的外部 baseline 对照；尽管当前外部 baseline 仍不能完全覆盖 DN 的全部系统能力，但现有证据已经足以支撑一套结构完整、结论克制且方法论上自洽的主实验章节。

## 附：主表写作口径建议

- 不要写：`DN 在交互延迟上优于所有外部 baseline`
- 建议写：`DN 在完整系统链路下返回可玩内容时保持了稳定的交互延迟，而外部 baseline 则分别代表权威互动对话、轻量文本生成与状态连续性等不同参考方向`

- 不要写：`LIGHT 与 DN 完全同类可比`
- 建议写：`LIGHT 作为当前最具权威性的互动对话 / 游戏世界候选 baseline，被纳入主表作为优先外部参照`

- 不要写：`WorldGeneration 已被完整忠实复现`
- 建议写：`WorldGeneration 当前以 supplementary fallback row 的形式保留，用于覆盖世界构造型系统的比较视角`

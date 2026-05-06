# 图表 caption 配套说明包（2026-04-26）

## 用途

本文件用于给当前实验章节中的关键表格与图形提供可直接放入论文模板的配套文字，包括：

- caption 候选
- 正文引用句
- 表后 / 图后结论句

当前优先服务以下材料：

- Table 1：统一 playable-latency 外部 baseline 主表
- Supplementary Table：WorldGeneration 补充比较表
- DN 原生主系统结果表
- Ablation：pregeneration / council / readwait

---

## 1. Table 1：外部 baseline 主表

### 推荐表名

`Table 1. Main playable-latency comparison between DN and runnable external baselines.`

### 中文 caption 候选

表 1 比较了 DN 与三个可运行外部 baseline 在统一 playable-latency protocol 下的交互等待效率。这里的 `first_playable_time_s` 表示从一次玩家点击开始，到系统返回第一份可继续游玩的内容所需的时间；`next_turn_time_s` 表示后续一轮玩家动作后系统再次返回可玩内容的时间。需要强调的是，这些 baseline 在系统形态上并不完全同构：`LIGHT` 代表权威互动对话 / 游戏世界候选系统，`Plan-Write-Revise` 代表轻量文本即时生成系统，`GenAgents` 代表多轮状态连续性补充系统。因此，该表更适合支持“DN 在完整系统链路下的可玩响应效率”这一主张，而不应被解读为所有系统功能范围完全等价的一对一竞赛。

另外，DN 行当前使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy；该口径成立于 DN 的预生成设置下，适合用于本轮主实验比较，但不等于全链路冷启动总时长。

### 正文引用句候选

- 如表 1 所示，我们将 DN 放在统一 playable-latency protocol 下，与三个角色不同但均已跑通的外部专门系统进行比较。
- 需要强调的是，表 1 的重点不是比较哪一个系统能最快生成任意一句文本，而是比较在“返回可继续游玩的内容”这一口径下，各系统的交互等待特征。
- DN 行当前采用 `generate_option` 阶段时延作为 `first_playable_time` 的工作 proxy，因此其结果应被解释为预生成设置下的首个可玩响应时延。

### 表后结论句候选

- 因此，表 1 支持的并不是“DN 绝对最快”，而是“DN 作为完整互动叙事系统，已经能够在可玩输出口径下与多个外部系统形成可执行对照”。
- 从主表的角色分工看，`LIGHT` 主要提供权威 external row，`Plan-Write-Revise` 提供速度参考，`GenAgents` 提供连续性补充，这一结构使主实验解释边界更清晰。

---

## 2. Supplementary Table：WorldGeneration 补充比较表

### 推荐表名

`Supplementary Table X. Runnable WorldGeneration fallback comparison under the playable-latency protocol.`

### 中文 caption 候选

补充表 X 展示了 `WorldGeneration` 在当前机器与当前复现路径下的可运行结果。需要说明的是，当前结果来自 fallback reconstruction path，而不是原论文意义上的完整 Evennia world pipeline。因此，该表的主要用途是补充“世界构造型系统”这一比较视角，而不是承担核心主表中的权威 external baseline 角色。

### 正文引用句候选

- 除主表之外，我们还保留了 `WorldGeneration` 的补充比较结果，以覆盖世界构造型系统的外部视角。
- 由于当前可运行路径属于 fallback reconstruction，而非完整原始 pipeline，`WorldGeneration` 更适合作为补充证据，而不宜继续承担主表结论压力。

### 表后结论句候选

- 因此，`WorldGeneration` 的价值主要在于提供任务形态相关性，而不是提供当前周期内最强的权威复现证据。

---

## 3. DN 原生主系统结果表

### 推荐表名

`Table X. Native end-to-end benchmark results of DN on DN-quality-benchmark-v1.`

### 中文 caption 候选

表 X 展示了 DN 在 `DN-quality-benchmark-v1` 上的原生主系统结果，包括结构化世界观生成、完整链路成功率以及关键阶段效率统计。结果表明，DN 在当前 benchmark 上能够稳定跑通完整任务链路，并在可用性护栏指标上保持较高一致性。

### 正文引用句候选

- 如表 X 所示，DN 在原生 benchmark 上已经具备稳定的端到端执行能力，而不仅仅是在局部模块上有效。
- 从表 X 可以看出，DN 在 `worldview_default_20` 与 `fullchain_default_20` 两条链路上都维持了较高成功率，说明当前系统具备完整流程可复现性。
- 原生主系统结果同时说明，DN 的主要耗时集中在后段完整内容生成，而不是前段规划搭建。

### 表后结论句候选

- 总体来看，原生主系统结果证明 DN 已形成一个稳定、可复现且能完整跑通任务流程的端到端系统。

---

## 4. Pregeneration Ablation

### 推荐表名

`Table/Section X. Effect of pregeneration on latency distribution and next-click experience.`

### 中文 caption / 引导句候选

该组实验用于分析 pregeneration 机制对 DN 延迟分布及下一次点击体验的影响。结果表明，pregeneration 的收益并不主要体现为压缩当前请求时延，而是通过将后续内容生成前移到玩家阅读窗口中，改善下一次点击的真实剧情命中率与等待时间。

### 正文引用句候选

- pregeneration 消融显示，关闭预生成会显著拉高 worldview 延迟分布，说明该机制对主链路效率具有实质影响。
- 从阈值分析结果可以看出，pregeneration 的收益具有明显的时间窗口敏感性，在约 `60s` 阅读窗口下最稳定。
- 与简单的“更快返回”不同，pregeneration 的核心价值在于提高下一次点击直接进入真实剧情的概率。

### 段后结论句候选

- 因此，pregeneration 更适合被解释为一种面向下一轮交互体验的异步准备机制，而不是单纯的当前请求优化。

---

## 5. Council Ablation

### 推荐表名

`Table/Section X. Effect of council on planning efficiency and pipeline reliability.`

### 中文 caption 候选

该组实验比较了默认配置与去除 council 模块后的运行差异，用于分析 council 对 DN 规划效率与完整流程稳定性的影响。结果显示，council 并非装饰性设计，而是会实质影响 worldview 阶段效率与 fullchain 成功率。

### 正文引用句候选

- council 消融结果表明，去除该模块后，worldview 平均延迟上升，且 fullchain 成功数由 `20/20` 降至 `19/20`。
- 从 council ablation 可以看出，DN 当前配置中的协同规划机制不仅影响输出组织质量，也影响系统执行的局部可靠性。

### 段后结论句候选

- 因此，council 应被视为 DN 规划链路中的关键支持模块，而非仅用于增强“思考感”的附加设计。

---

## 6. Readwait Figures

### 推荐图名 1

`Figure X. Comparison of next-click latency under different readwait settings.`

### 推荐图名 2

`Figure Y. Real-scene hit rate under different readwait settings.`

### 图 caption 候选

图 X 展示了在不同 readwait 配置下，玩家第二次点击所对应的等待时间分布。图 Y 展示了不同配置下第二次点击直接命中真实剧情的比例。二者共同反映了读取等待策略并不是单纯的时间参数，而会影响系统是否能够返回可继续推进的真实剧情。

### 正文引用句候选

- 如图 X 和图 Y 所示，readwait 的主要作用并不体现在数量级上的时延变化，而是体现在真实剧情命中率的改善上。
- 图 Y 表明，在当前实现下，适当的 readwait 配置能够显著提高 real-scene hit rate，这对实际交互体验比单纯压缩毫秒级延迟更重要。

### 图后结论句候选

- 因此，readwait 更适合被解释为一种与输出质量耦合的调度机制，而不是纯粹的等待开关。

---

## 7. 实验章节中的衔接句

### DN 原生结果 -> 主实验表

- 在确认 DN 原生系统已经稳定可运行之后，我们进一步引入外部 baseline，以考察其在统一 playable-latency 口径下的相对位置。

### 主实验表 -> 补充表

- 主表之外，我们还保留 `WorldGeneration` 的补充比较结果，用于覆盖世界构造型系统这一更接近 DN 任务形态的视角。

### 主实验 / 补充表 -> 消融

- 在外部 baseline 对比说明 DN 并非只在自建协议中成立之后，我们进一步通过消融实验解释 DN 当前配置为何能够形成上述结果。

### 消融 -> 局限性

- 尽管上述结果已经构成一套较完整的主实验叙事，但 baseline 覆盖与系统同构性仍存在现实边界，因此仍需对当前可比范围保持克制解释。

---

## 8. 最推荐直接复制使用的三句

- `Table 1` 结论句：表 1 说明，DN 已经能够在统一 playable-latency 口径下，与多个可运行外部系统形成具有方法学约束的实验对照。
- `Supplementary Table` 结论句：补充表中的 `WorldGeneration` 结果主要用于覆盖世界构造型系统视角，而不承担当前周期核心主表的权威 external row 角色。
- `Ablation` 结论句：消融实验进一步说明，DN 当前配置中的 pregeneration、council 与 readwait 模块都对最终系统行为产生了实质影响。

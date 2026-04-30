# 4.x 文本侧 Baseline 对比实验

## 4.x.1 实验目的

为了验证 DN 在文本侧剧情规划与状态组织上的有效性，我们引入当前最适合作为外部文本 baseline 的开源系统 `GenAgents`，并围绕同一批 benchmark 样本进行对齐比较。这里的目标不是寻找一个与 DN 完全同构的系统，而是构建一个在“文本规划、角色一致性、多轮连续性”维度上具有代表性的外部参照，从而为主实验提供更有说服力的对比对象。

考虑到 DN 与 GenAgents 的原生输出形式并不一致：DN 输出的是 structured worldview planning 结果，而 GenAgents 输出的是 persona-conditioned multi-turn response，因此我们采用“任务对齐而非输出同构”的比较策略。具体而言，我们从 `genagents_consistency_subset_v2` 中固定 8 个 benchmark ID，并从 DN 现有 `benchmark_v1_worldview_default_20` 结果中抽取同样的 8 个样本，形成对齐后的 Table 2 对比集。

## 4.x.2 对比设置

在 DN 侧，我们采用现有已稳定跑通的 `benchmark_v1_worldview_default_20` 结果，并从中筛出与 GenAgents 子集一致的 8 个样本，构建 matched subset row。该设置反映的是 DN 在“结构化世界观生成”链路上的稳定性与效率。

在 GenAgents 侧，我们使用 DN 现有 `.env` 中的 OpenAI-compatible provider 配置完成 live run，并采用固定 3-turn consistency protocol 对 8 个样本进行评测。为避免仅依赖弱启发式指标，我们进一步引入了 judge-based rubric，对 theme alignment、setting adherence、persona consistency、multi-turn coherence 和 actionability 五个维度进行打分。

需要强调的是，两侧的输出形态并不相同，因此 Table 2 中真正可以直接比较的是：样本覆盖范围、运行成功率、系统级延迟，以及广义上的文本侧场景适配能力；而 persona consistency 等 judge-based 分数更适合作为 GenAgents 的质量描述，而不能被机械地解释为与 DN worldview row 的一一对应指标。

## 4.x.3 实验结果

在对齐后的 8 样本子集上，DN 保持了 `success_rate = 1.0`，平均延迟为 `31.733 s`，`p95` 延迟为 `57.283 s`。这说明 DN 在当前文本规划链路上具有较高的执行稳定性，但结构化世界观生成也带来了较高的时间开销。

相比之下，GenAgents 在同一 8 样本子集上取得了 `item_full_success_rate = 0.875`、`turn_success_rate = 0.958`、`latency_mean_s = 7.343` 和 `latency_p95_s = 11.425`。从效率角度看，GenAgents 明显更轻量，说明其在响应式文本生成任务中具有更低的执行成本；但从系统可靠性角度看，它仍然存在少量失败项，当前最典型的失败样本为 `DNQBV1_009`，其中出现了 blocked turn，因此尚未达到 DN 在 matched subset 上的稳定性水平。

在质量维度上，GenAgents 的 judge-based 结果显示：`persona_consistency_mean_1to5 = 5.0`，`setting_adherence_mean_1to5 = 4.875`，`multi_turn_coherence_mean_1to5 = 4.75`，`actionability_mean_1to5 = 4.875`。这表明其在多轮角色连续性、场景贴合度与行动建议可用性上表现较强，能够作为 DN 在文本侧状态一致性与多轮交互能力上的有效外部 baseline。

## 4.x.4 结果分析

上述结果说明，DN 与 GenAgents 分别代表了两类不同的文本侧系统取向。DN 更偏向于“结构化规划优先”：它通过生成较完整的世界观组织结果来支撑后续互动，因此在稳定性上表现更强，但代价是延迟更高。GenAgents 则更偏向于“角色响应优先”：它能够以更低成本给出具有较强 persona consistency 的多轮文本反应，但在复杂样本上仍可能出现局部失败。

因此，本文不应将这一组结果简单表述为“DN 全面优于 GenAgents”或“GenAgents 全面优于 DN”。更准确的结论是：在 matched subset 上，DN 展现出更高的结构化规划稳定性，而 GenAgents 展现出更高的响应效率和较强的多轮角色一致性。两者的差异本质上来自系统目标与输出机制的不同，而不是单一维度上的绝对优劣。

从论文写作角度看，这一结果足以支持以下主张：`GenAgents` 可以作为 DN 的 `text-side planning / state-consistency baseline`，为 DN 在文本规划、角色稳定性与多轮一致性方面提供外部参照；但它不能替代 DN 的完整多模态互动系统 baseline，也不应被用于图像质量、图文协同或 branching option diversity 等维度的直接对标。

## 4.x.5 局限性与威胁

本组实验仍有三个需要明确说明的限制。第一，DN 与 GenAgents 的输出形式不同，因此当前比较属于“任务对齐比较”，而不是“同构输出比较”。第二，GenAgents 的质量指标目前基于 judge-based 评分，虽然已经明显强于先前的启发式占位指标，但仍不能等同于人工金标准。第三，当前可执行的强 baseline 主要集中在文本侧；AIDungeon 因 legacy runtime 问题在本轮主实验周期内被判定为 no-go，StoryDiffusion 则因当前机器缺乏 CUDA 条件而被保留为 deferred visual-subexperiment branch。

综上，当前 Table 2 的最安全表述应为：DN 与 GenAgents 在文本侧具有可比性，这种可比性建立在 matched subset 与任务对齐之上；DN 的优势主要体现为结构化规划稳定性，GenAgents 的优势主要体现为轻量响应效率与角色连续性。

# Table 2 Results Draft (ZH, 2026-04-26)

在文本侧 baseline 对比中，我们选择了与 DN 任务目标最接近且当前能够稳定复现的开源系统 `GenAgents`，并在 `genagents_consistency_subset_v2` 的 8 个样本上完成了多轮一致性评测。为减少口径偏差，我们进一步从 DN 的 `benchmark_v1_worldview_default_20` 中抽取了同样的 8 个 benchmark ID，构建了对齐后的比较表，而不是直接使用 20 样本 DN 行与 8 样本 baseline 行进行松散并列。

从运行可靠性看，GenAgents 在该 8 样本子集上取得了 `turn_success_rate = 0.958` 和 `item_full_success_rate = 0.875`，说明其作为文本侧外部 baseline 已经具备稳定产出能力，但仍存在少量失败项；当前主要失败样本为 `DNQBV1_009`，其中出现了一个 blocked turn。相比之下，DN 在同一 8 样本 worldview 子集上保持了 `success_rate = 1.0`，说明 DN 在当前文本规划链路上的执行稳定性更强。

从效率上看，GenAgents 的 `latency_mean_s = 7.343`、`latency_p95_s = 11.425`，显著低于 DN worldview 规划子集的平均与长尾延迟。这说明外部 baseline 在纯文本响应式任务下具有更轻量的执行路径，而 DN 的结构化 worldview 规划链路则带来了更高的计算与组织成本。因此，这一结果更适合被解释为“系统目标不同带来的效率差异”，而不是简单地得出“某一系统全面优于另一系统”的结论。

从质量侧看，GenAgents 在 judge-based 指标上表现较强，`persona_consistency_mean_1to5 = 5.0`，`setting_adherence_mean_1to5 = 4.875`，`multi_turn_coherence_mean_1to5 = 4.75`，`actionability_mean_1to5 = 4.875`。这说明其在多轮角色稳定性、语境延续和即时行动建议方面具备较强能力，适合作为 DN 在“角色一致性 / 多轮文本交互”维度上的外部参照。然而，DN 当前这一行对应的是 structured worldview generation，而非 persona-conditioned multi-turn dialogue，因此这两类质量指标不能被当作完全同构的逐项数值比较。

基于以上结果，我们建议在论文中将 GenAgents 明确定位为 `text-side planning / state-consistency baseline`：它可以有效支撑 DN 在文本规划、角色稳定性和多轮一致性方面的对比讨论，但不能替代 DN 的完整多模态互动系统 baseline。换言之，当前 Table 2 的安全结论应当是：DN 与 GenAgents 在文本侧具有可比性，但这种可比性属于“任务对齐”而非“输出完全同构”。

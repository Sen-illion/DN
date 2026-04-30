# Table 1 Caption Draft (ZH, 2026-04-26)

## Caption 长版

表 1 比较了 DN 与若干外部专门系统在统一 playable-latency protocol 下的交互效率。这里的 `first_playable_time_s` 表示从一次玩家点击触发开始，到系统返回第一份可继续游玩的内容所需的时间；`next_turn_time_s` 表示后续一轮玩家动作后系统继续返回可玩内容的时间。需要注意的是，这些 baseline 在系统形态上并不完全同构：`LIGHT` 代表权威互动对话 / 游戏世界候选系统，`Plan-Write-Revise` 代表轻量文本即时生成系统，`GenAgents` 代表多轮状态连续性补充系统。因此，该表更适合支持“DN 在完整系统链路下的可玩响应效率”这一主张，而不应被解读为所有系统在功能范围上完全等价的一对一竞赛。

另外，DN 行当前使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy；这一口径成立于 DN 的预生成设置下，应用于本轮主实验的统一效率比较，但不应被误读为“从零冷启动到全部系统资源完成”的总时长。

## Caption 短版

表 1：DN 与外部专门 baseline 在统一 playable-latency protocol 下的效率比较。`LIGHT` 用作权威互动对话 baseline，`Plan-Write-Revise` 用作轻量文本速度参考，`GenAgents` 用作多轮连续性补充 baseline。DN 行的 `first_playable_time_s` 当前使用 `generate_option` 阶段时延作为 proxy。

## 正文引用句建议

- 如表 1 所示，我们将 DN 放在统一 playable-latency protocol 下，与三个角色不同但均可运行的外部专门系统进行比较。
- 需要强调的是，表 1 的重点不是比较哪一个系统能最快生成任意一句文本，而是比较在“返回可继续游玩的内容”这一口径下，各系统的交互等待特征。
- DN 行当前采用 `fullchain generate_option latency` 作为 `first_playable_time` 的工作 proxy，因此其结果应被解释为预生成设置下的首个可玩响应时延，而不是全链路冷启动总时长。

## 补充表引用句建议

- 另外，我们保留了 `WorldGeneration` 的补充比较结果，以覆盖世界构造型系统；但由于当前可运行路径仍属 fallback reconstruction，因此未将其纳入核心主表。

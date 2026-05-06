# 主实验正文段落稿（可直接改写进论文）

## 版本 A：偏稳健

为了检验 DN 在真实交互链路中的响应效率，我们构建了统一的 playable-latency protocol，并将比较目标限定为“从玩家触发一次交互，到系统返回一份可继续游玩的内容”这一过程。在这一设定下，我们选择了三个已实际跑通的外部 baseline：`LIGHT` 作为权威互动对话 / 游戏世界候选系统，`Plan-Write-Revise` 作为轻量文本即时生成速度参考，`GenAgents` 作为多轮状态连续性补充 baseline。结果表明，DN 在当前预生成设置下的 `first_playable_time_s` 工作 proxy 为 `7.662s`；与此同时，轻量文本类 baseline 在即时文本响应上更快，例如 `LIGHT` 与 `Plan-Write-Revise` 的首轮时延分别为 `0.41s` 与 `0.833s`。因此，本实验并不支持“DN 在所有外部系统中绝对最快”这一表述。

更准确地说，表 1 说明的是：在完整系统链路下，DN 能够稳定返回结构化的可继续游玩内容，而不是仅仅输出一句即时文本回复。换言之，DN 的结果应结合系统完整性进行解释，而不能简单等同于轻量对话模型或单段故事生成器的局部响应时间。与强调状态连续性的 `GenAgents` 相比，DN 的当前交互时延并不处于明显劣势，这说明在引入完整互动叙事结构后，DN 仍维持了可接受的玩家等待范围。需要额外说明的是，DN 行当前使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy，因此其含义是预生成设置下的首个可玩响应时延，而不是全链路冷启动总时长。

## 版本 B：偏结果段

表 1 给出了 DN 与外部专门 baseline 在统一 playable-latency protocol 下的效率比较。我们以 `first_playable_time_s` 和 `next_turn_time_s` 衡量玩家触发后系统返回可继续游玩内容所需的时间，并以 `success_rate` 与 `p95_latency_s` 评估稳定性。结果显示，DN 在当前配置下的 `first_playable_time_s` 工作 proxy 为 `7.662s`。外部轻量文本型 baseline 在即时文本生成上更快，例如 `LIGHT` 的首轮时延为 `0.41s`，`Plan-Write-Revise` 为 `0.833s`；而 `GenAgents` 的首轮时延为 `9.76s`，后续一轮时延为 `6.285s`。

这些结果表明，DN 的优势不宜被表述为“绝对最低的文本生成延迟”，而应被表述为“在完整互动叙事系统链路下，仍能以稳定方式返回可玩内容”。因此，我们将 `LIGHT` 作为主表中的优先权威外部 baseline，将 `Plan-Write-Revise` 作为速度参考，将 `GenAgents` 作为连续性交互补充 baseline；同时将 `WorldGeneration` 保留在补充比较中，用于覆盖世界构造型系统。需要注意的是，DN 行当前采用 `generate_option` 阶段时延作为 `first_playable_time_s` 的工作 proxy，因此该结果应理解为首个可玩响应时延，而不是从零冷启动到完整资源完成的总等待时间。

# DN 主实验结果解释（2026-04-26）

## 1. 本轮主实验到底在比较什么

本轮主实验不再试图证明“DN 在所有内容维度上全面优于所有外部系统”，而是聚焦一个更清晰、也更符合当前证据边界的问题：

- 在统一 benchmark 主题约束下，当玩家触发一次交互后，系统需要多久才能返回一份“现在就能继续玩”的内容？

因此，当前主实验的核心指标固定为：

- `first_playable_time_s`
- `next_turn_time_s`
- `success_rate`
- `p95_latency_s`
- `playable_output_completeness`
- `interaction_continuity`

本轮主实验不再把以下指标作为核心结论：

- `end_to_end_boot_time_s`
- 从零生成全部世界观、角色、图像和其他资源后的完整冷启动时间

## 2. 固定版主表 baseline stack

当前核心主表已经固定为四行：

1. `DN`
2. `LIGHT`
3. `Plan-Write-Revise`
4. `GenAgents`

对应文件：

- 核心主表：`../1_table1_main_visual_efficiency/summary_tables/main_playable_latency_scaffold_2026-04-26.csv`
- `WorldGeneration` 补充表：`../1_table1_main_visual_efficiency/summary_tables/supplementary_playable_latency_worldgeneration_2026-04-26.csv`

这意味着：

- `LIGHT` 是当前最优先的权威 external row
- `Plan-Write-Revise` 是速度参考 row
- `GenAgents` 是连续性补充 row
- `WorldGeneration` 不再承担核心主表结论压力

## 3. 每个 baseline 在主表中的角色应该怎么写

### 3.1 DN

DN 是“带预生成机制的完整互动叙事系统”。

在当前主表中，DN 行代表：

- 真实 DN 系统在现有预生成设置下的交互等待特征
- 不是一个纯文本模型，而是完整系统链路中的“玩家点击到可玩内容返回”结果

需要额外说明的是：

- DN 行当前使用 `fullchain generate_option latency` 作为 `first_playable_time_s` 的工作 proxy
- 这一口径可用于当前主实验，但不等于“从零冷启动到全部资源完成”的完整系统总时长

### 3.2 LIGHT

`LIGHT` 是当前主表中最重要的外部权威 row。

它进入主表的主要原因不是“当前内容最贴合 DN”，而是：

- 上游项目权威性更强
- 任务形态更接近互动对话 / 游戏世界候选系统
- 相比 `WorldGeneration` 当前 fallback 路径，更适合作为对审稿人可解释的外部主表参照

但必须明确写清楚：

- 当前跑通的是其公开 checkpoint 的 text-side 可运行切片
- 不是完整 LIGHT 在线世界服务
- 当前结果更适合作为“权威 external latency/reference row”
- 不能把它写成与 DN 完全同构的完整游戏系统

### 3.3 Plan-Write-Revise

`Plan-Write-Revise` 不是完整游戏系统，而是专门的故事生成方法。

它在当前主表中的意义主要是：

- 提供“按需即时生成文本剧情”的速度参考
- 说明轻量文本生成器在即时文本响应上可以非常快
- 但它不是 DN 那种完整互动叙事系统的等价替代物

正文建议将其固定写成：

- `speed/reference baseline`

### 3.4 GenAgents

`GenAgents` 不适合作为完整游戏 baseline，但非常适合作为：

- 多轮交互稳定性
- 状态连续性
- 下一轮可继续玩响应

方面的补充对照。

因此正文建议将其固定写成：

- `continuity supplement baseline`

## 4. 当前主表结果应该如何解释

按当前主表数据：

- DN：`first_playable_time_s = 7.662`
- LIGHT：`first_playable_time_s = 0.41`
- Plan-Write-Revise：`first_playable_time_s = 0.833`
- GenAgents：`first_playable_time_s = 9.76`

可以得出以下稳妥解释。

### 4.1 DN 并不是“绝对最快”

这一点必须正面承认。

在当前主表中：

- `LIGHT` 和 `Plan-Write-Revise` 都比 DN 更快返回第一份可玩文本

因此不能把主实验写成：

- “DN 在交互等待时间上全面优于所有外部 baseline”

### 4.2 DN 的优势应解释为“完整系统链路下仍保持可用延迟”

更准确的写法是：

- DN 虽然不是最轻量的文本响应器，但它返回的不是一句孤立短文本，而是完整系统中的可继续游玩的互动内容
- 因而 DN 的延迟应放在“系统完整性”和“可玩输出结构”背景下解释

也就是说，DN 当前更适合 claim：

- `system-complete playable response under controlled latency`

而不是：

- `lowest latency among all baselines`

### 4.3 LIGHT 和 PWR 的快，说明的是轻量外部系统在即时文本生成上的天然速度优势

这两行结果主要说明：

- 如果只比较轻量外部模型在单模型条件下即时吐出一段文本，它们当然可能更快

这并不自动推翻 DN，因为 DN 的比较对象不是：

- “一句话生成器”

而是：

- “完整互动叙事系统中的可继续游玩响应”

### 4.4 GenAgents 的意义在于说明：即使是强状态连续性 baseline，也未必在当前口径下全面优于 DN

当前结果：

- DN 的 first-playable proxy 为 `7.662s`
- `GenAgents` 的 `first_playable_time_s` 为 `9.76s`
- `GenAgents` 的 `next_turn_time_s` 为 `6.285s`

这支持一个相对稳妥的说法：

- 与强调状态连续性的外部 agent 系统相比，DN 的当前交互延迟并不处于明显劣势

## 5. 为什么 WorldGeneration 只能进补充表

`WorldGeneration` 当前没有被删除，而是被降为补充表，原因不是它没有价值，而是：

1. 当前真正跑通的是 fallback reconstruction path
2. 不是完整复现原论文 pipeline
3. 因此把它放进核心主表，会削弱主表“权威 external row”这一层说服力

但它仍然有保留价值：

- 它比 `LIGHT` 更像世界构造型系统
- 可用于补充说明 DN 也参考了世界构造方向的外部系统

因此建议固定写法是：

- 主表使用 `LIGHT`
- 补充表保留 `WorldGeneration`

## 6. 当前最应该避免的危险表述

以下说法现在不应出现：

- “DN 在交互延迟上优于所有外部 baseline”
- “LIGHT 与 DN 完全同类可比”
- “WorldGeneration 已被完整忠实复现”
- “外部 baseline 已全面覆盖 DN 的全部系统能力”

## 7. 当前最安全的论文表述

以下说法目前是安全且与证据一致的：

- DN 已经在统一 playable-latency protocol 下与多个外部专门系统完成对照
- `LIGHT` 作为当前最具权威性的互动对话 / 游戏世界候选系统，被纳入核心主表作为优先 external row
- `Plan-Write-Revise` 提供了轻量文本即时生成的速度参考
- `GenAgents` 提供了多轮状态连续性的补充对照
- `WorldGeneration` 作为世界构造型系统被保留在补充比较中
- DN 的结果应在“完整系统可玩响应”而不是“单句文本生成速度”背景下解释

## 8. 当前最推荐的正文叙述骨架

如果现在就写主实验结果段，最推荐的结构是：

1. 先定义比较目标
   - 比较的是“玩家点击到返回可继续玩的内容”的等待时间
2. 再定义 baseline 角色
   - `LIGHT` = 权威 external row
   - `Plan-Write-Revise` = speed/reference row
   - `GenAgents` = continuity supplement row
3. 然后解释结果
   - DN 不是最轻量文本生成器
   - 但 DN 返回的是完整系统中的可玩响应
   - 因而需要结合系统完整性解释时延
4. 最后给出边界
   - 当前外部 baseline 仍不能完全覆盖 DN 的全部系统能力

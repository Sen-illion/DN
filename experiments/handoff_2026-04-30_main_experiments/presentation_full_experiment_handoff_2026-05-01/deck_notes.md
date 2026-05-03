# DN 全量实验总结 deck notes

- 生成时间：2026-05-01 01:08:03.493149
- PPTX：`D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\presentation_full_experiment_handoff_2026-05-01\DN_full_experiment_handoff_detailed_2026-05-01.pptx`
- PDF：`D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\presentation_full_experiment_handoff_2026-05-01\DN_full_experiment_handoff_detailed_2026-05-01.pdf`

## Slide 01 · DN 项目实验全景总结
- section: 研究汇报
- conclusion: 这份汇报聚焦三件事：DN 是什么、实验如何设计、当前最正式的结果是什么。
- note: 2026-05-01 · DN 实验汇报版

## Slide 02 · DN 是什么
- section: 研究汇报
- conclusion: DN 的目标不是一次性生成文本，而是持续推进可交互叙事。
- bullets:
  - 输入可以是一个主题、一段设定，或一个待展开的故事想法。
  - 系统需要先组织世界、角色与剧情，再返回一个可继续游玩的当前状态。
  - 玩家做出选择后，系统还要继续生成下一轮文本或图像内容。

## Slide 03 · 汇报结构
- section: 研究汇报
- conclusion: 主 deck 讲问题、方法、结果与结论；附录只负责补充证据。
- bullets:
  - 前 18 页先回答：DN 在做什么、实验在比什么、哪些结果最值得引用。
  - 附录再补充：原始路径、历史 run、schema、远程环境与已知问题。
  - 正式结果与 smoke / fallback / blocker 已经分层，不能混成同一口径。

## Slide 04 · 研究问题
- section: 研究汇报
- conclusion: 这些实验不是为了堆 baseline，而是为了回答 DN 当前的真实进展。
- bullets:
  - 问题 1：DN 自己的完整链路是否稳定，时间主要花在哪。
  - 问题 2：如果和外部文本方法比较，DN 的 playable latency 处在什么位置。
  - 问题 3：如果和图像方法比较，哪些 baseline 已经真正跑通并形成正式对照。

## Slide 05 · 实验全景地图
- section: 研究汇报
- conclusion: 目前形成的是四条证据线并行推进，而不是单一目录里的零散结果。
- note: 四条线分别回答：自身效率、图像对照、DOC 接入、样例与状态整理。

## Slide 06 · 当前正式结果边界
- section: 研究汇报
- conclusion: formal20 图像双主表是当前最正式的主结果；其余材料用于补证据与解释边界。
- note: 正式主结果、辅助证据、历史探索已经分层。

## Slide 07 · 主实验到底在比什么
- section: 研究汇报
- conclusion: A组与 B组形态不同，但都在回答“用户要等多久，故事才能继续”。
- note: 重要口径：两组不是完全同构系统，不能被讲成单一竞技榜单。

## Slide 08 · 统一主实验总表
- section: 研究汇报
- conclusion: 这一页是汇报核心：DN 作为统一锚点，把两类对照组放进同一上位问题。
- note: 显著口径说明：A组衡量可继续游玩的文本响应；B组衡量点击后下一张剧情图响应。

## Slide 09 · 统一主实验总览图
- section: 研究汇报
- conclusion: 整体看，SDM-v2 最快，IC-LoRA 最慢；DN 在文本组中处于中等偏慢位置。
- note: 这张图展示的是“故事继续推进时，用户等待时间的量级分布”。

## Slide 10 · A组：文本 / 可玩响应组在测什么
- section: 研究汇报
- conclusion: A组更适合回答“可玩响应效率”，而不是图像连续性。
- bullets:
  - DN：我们的系统，强调完整交互链路。
  - LIGHT：权威互动文本 / game-world 参考基线。
  - PWR：速度参考型故事生成基线。
  - GenAgents：多轮状态维持与连续性补充基线。
- note: 样本量并不完全相同，因此更适合做相对位置参考。

## Slide 11 · A组结果解读
- section: 研究汇报
- conclusion: 外部文本系统里存在更快的方法，但 DN 的价值不只在速度，还在完整系统形态。
- bullets:
  - LIGHT 和 PWR 响应更快，但它们和 DN 的语义形态并不完全等同。
  - GenAgents 首轮更慢、下一轮更快，更像连续性补充行。
  - DN 的 7.662s 应理解为“当前完整链路下的 first-playable proxy”。

## Slide 12 · B组：图像剧情延续组在测什么
- section: 研究汇报
- conclusion: B组聚焦图像剧情延续，最贴近“点击后继续出下一张图”的体验。
- bullets:
  - 统一样本集：formal20。
  - 统一 next-turn 协议：固定动作模板，避免 baseline 自带交互不一致。
  - 统一输入风格：DN-style prompt adaptation，保证主题与冲突大体可比。
  - 统一输出：result.json / summary.json / 样例图。

## Slide 13 · B组结果：first-turn
- section: 研究汇报
- conclusion: 首张剧情图速度上，SDM-v2 最快，StoryDiffusion 居中，IC-LoRA 明显最慢。
- bullets:
  - SDM-v2：2.847s，速度优势最明显。
  - StoryDiffusion：7.69s，在连续图能力和时延之间较平衡。
  - IC-LoRA：30.06s，workflow 更重，因此速度成本最高。

## Slide 14 · B组结果：next-turn
- section: 研究汇报
- conclusion: next-turn 是最接近真实交互体验的指标：点击动作后，要等下一张图多久。
- bullets:
  - StoryDiffusion：8.495s。
  - SDM-v2：2.827s。
  - IC-LoRA：30.057s。
  - 排序与 first-turn 基本一致，说明系统开销结构相对稳定。

## Slide 15 · B组稳定性、连续性与样例图
- section: 研究汇报
- conclusion: formal20 上三条图像 baseline 都已形成稳定、可追溯、可审图的正式结果包。
- bullets:
  - formal20：3 条 baseline 都达到 20/20 success。
  - next_turn continuation_success_rate = 1.0。
  - interaction_continuity = 1.0。
- note: 样例 sheet 的行：first_turn / next_turn current / next_turn next；列：StoryDiffusion / SDM-v2 / IC-LoRA。

## Slide 16 · DOC baseline 当前进展
- section: 研究汇报
- conclusion: DOC 的现实价值在于：已经能稳定产出可比较数据集，而不是 upstream 全栈已复现。
- note: 正式可用表述：faithful DOC-style fallback artifact for DN comparison pipeline。

## Slide 17 · DN 内部 benchmark 说明了什么
- section: 研究汇报
- conclusion: DN 当前真正慢的主要是世界观与主角生成，而不是“生成选项”这一步。
- bullets:
  - 世界观默认均值 33.657s；去 council 后仍有 20.031s。
  - generate_option 中位仅 0.022s，不是主瓶颈。
  - main_character 中位 56.546s，说明部分前置生成很重。

## Slide 18 · 结论与后续工作
- section: 研究汇报
- conclusion: 当前最稳的汇报主线是 formal20 图像主表 + DOC fallback + DN 历史 latency 表。
- note: 如果继续扩展，优先沿用 formal20 协议与现有 runner。

## Slide 19 · 附录
- section: 补充材料
- conclusion: 附录页用于补充原始路径、历史过程与已知问题。

## Slide 20 · 实验资产目录图
- section: 补充材料
- conclusion: 这套整理目录就是当前汇报材料与原始证据的统一入口。

## Slide 21 · formal20 图像 baseline raw artifact 路径总表
- section: 补充材料
- conclusion: 正式图像主实验的 source-of-truth 在这些目录，不需要再去猜。
- note: 完整路径见 CURRENT_GROUND_TRUTH.md 与 image_baselines_formal20/README.md。

## Slide 22 · smoke3 / formal8 / blocker / fallback 历史图像实验索引
- section: 补充材料
- conclusion: 历史 run 需要保留，但只能作为过程证据，不能替代 formal20 主表。
- note: 重点是解释为什么最后 formal20 主表会固定成 StoryDiffusion / SDM-v2 / IC-LoRA。

## Slide 23 · DOC raw fallback 与 normalized copy 对照
- section: 补充材料
- conclusion: 两个目录都保留：一个强调原始产物，一个强调统一 schema 可读取。
- note: 推荐主讲法：可用，但 fallback-oriented，而非 upstream-authentic。

## Slide 24 · DN 历史 playable-latency 原表摘录
- section: 补充材料
- conclusion: 如果要谈 DN 和文本基线的历史对比，这页是最短入口。
- note: WorldGeneration 行是 supplementary，不在主表核心 4 行里。

## Slide 25 · DN benchmark 内部指标原表摘录
- section: 补充材料
- conclusion: 这页用来支撑“时间到底花在哪”。
- note: source-of-truth：benchmark_v1_summary_metrics.csv / .json / .xlsx。

## Slide 26 · 当前已知问题
- section: 补充材料
- conclusion: 已知问题定义了当前结果的解释边界。
- note: 最重要的边界：SDM-v2 仓库下线、DOC 不是 full upstream reproduction。

## Slide 27 · 远程 4090 环境与复现入口
- section: 补充材料
- conclusion: 如果继续复跑实验，先找 runner、subset、schema，再进入远程 4090 环境。
- note: 当前远程工作根：/root/autodl-tmp/outputs。

## Slide 28 · 代表样本说明页
- section: 补充材料
- conclusion: 看样例时，最重要的是横向比 baseline，纵向比 first-turn 与 next-turn 连续性。
- bullets:
  - 行含义：first_turn、next_turn current、next_turn next。
  - 列含义：StoryDiffusion、SDM-v2、IC-LoRA。
  - 适合看 continuity、首图画质、角色/场景延续。
- note: 已知替代图：SDM-v2 DNQBV1_009、IC-LoRA DNQBV1_007。

## Slide 29 · 哪些结果不能混用
- section: 补充材料
- conclusion: 把 smoke、blocker、public fallback 与 formal20 正式结果混在一起，会直接破坏口径。

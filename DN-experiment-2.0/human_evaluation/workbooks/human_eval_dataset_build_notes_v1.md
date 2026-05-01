# Human Evaluation Dataset Build Notes v1

## 数据源
- `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\theme_*`：用于抽取连续剧情文本、图片路径和图片对应场景说明。
- `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\图片一致性_experiment\multiview_image_consistency\results\latest_eval_manifest.jsonl`：用于定位可用图片样本清单。
- `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\human_evaluation\templates\human_rating_template_v1.csv` 和 `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\human_evaluation\schemas\human_rating_v1.schema.json`：用于复用英文标准评分字段。
- `C:\Users\User\Desktop\DN-main\DN-experiment-2.0\human_evaluation\scripts\summarize_human_ratings.py`：用于字段可汇总性轻量检查。

## 样本数量
- 文本样本：10 条（pilot）。
- 图片样本：30 条（pilot）。
- 校准样本：文本 1 条、图片 1 条，已在样本页标记。

## 样本选择与整理
- 文本样本从每个 theme 目录中抽取前 3 个连续剧情片段，合并为可阅读的中文剧情文本。
- 图片样本从图片一致性 manifest 中抽取，逐条确认本地图片存在，并读取相邻 JSON 中的中文剧情段落作为场景说明。
- 所有正式样本使用 `TEXT_0001` / `IMG_0001` 形式匿名化；评测员不需要看到原始 game id 或实验路径。
- 给评测员看的内容包括：样本编号、自然语言摘要/剧情/图片、关注人物/物体/场景要求、评分说明。
- 不给评测员看的内容包括：模型名、实验组名、LLM 分数、API 信息、生成参数、JSON 原始结构。技术追踪列已隐藏或放在右侧。

## 排除的数据类型
- 图片路径不存在的样本。
- 缺少可读剧情/场景 JSON 上下文的图片样本。
- 只有 LLM 评分但无法组成自然语言测评材料的记录。
- 任何正式样本均未纳入 LLM judge 分数或模型名称。

## 失效图片路径
- 排除记录总数：0。
- 按原因统计：无。

## 匿名化和字段设计
- `sample_id` 与展示编号一致，均为匿名 ID。
- 评分表右侧保留英文标准字段：文本 `text_coherence_1to5`；图片 `overall_score`、`semantic_consistency`、`subject_attribute_consistency`、`spatial_consistency`、`style_lighting_consistency`、`detail_integrity` 等。
- 英文字段通过公式引用中文填写列，便于后续另存为 CSV 后使用现有汇总脚本。

## 质量检查结果
- 文本 Excel 存在：True。
- 图片 Excel 存在：True。
- 文本评分字段检查：True
- 图片评分字段检查：True
- 图片路径存在性检查：True
- 技术信息泄露扫描：True
- 现有汇总脚本读取检查：True

## 不完整或需人工确认
- 图片关键人物/物体/动作说明基于当前 JSON 的剧情文本和 prompt_json 自动整理，建议项目负责人抽查 3-5 条确认说明是否符合实验意图。
- 本版本是 pilot 包，适合先发给 2-3 名评测员独立评分；如需 full 版本，可复用构建脚本扩大抽样数量。
# Overview

## 当前最重要的变化

现在的实验叙事已经从“把文本表和图像表并排讲”改成了两层结构：

### 第一层：严格主实验

严格主实验只比较：

- `DN`
- `StoryDiffusion`
- `SDM-v2`
- `IC-LoRA`

严格主实验的上位问题是：

- 用户点击后，系统还要多久才能把下一轮内容交付出来

对应主表：

- `D:\Projects\DN\experiments\handoff_2026-04-30_main_experiments\01_main_tables\strict_fullready_main_comparison_2026-05-01.csv`

### 第二层：历史文本参考

历史文本参考继续保留：

- `DN`
- `LIGHT`
- `PWR`
- `GenAgents`

但这组表现在只回答：

- 文本 playable response 多快

它们不再与严格主实验表混写成同一口径。

## 现在最值得先看的结果

### 严格主表
- `..\01_main_tables\strict_fullready_main_comparison_2026-05-01.csv`

### DN 新 full-ready 结果
- `D:\Projects\DN\experiments\benchmark\standard_runs\benchmark_v14_fullready_nextturn_20_summary.json`

### 图像 baseline 正式 formal20 表
- `..\01_main_tables\first_turn_formal20_summary.csv`
- `..\01_main_tables\next_turn_formal20_latency_summary.csv`

## 什么是 primary，什么是 secondary

### Primary / current ground truth
- strict full-ready main table
- DN normal20 / pregen60s20 full-ready runs
- formal20 image baseline first-turn / next-turn tables
- formal20 quality review

### Secondary / historical / debugging evidence
- smoke3 runs
- formal8 runs
- blocker runs
- public fallback rows
- DOC fallback artifacts
- historical text playable-latency tables

## 目录建议阅读顺序

- `RESULT_MAP.md`: 按用途找路径
- `..\01_main_tables\TABLE_GUIDE.md`: 看每张表到底回答什么问题
- `..\01_main_tables\MASTER_SUMMARY.md`: 看严格主表和历史文本参考之间的关系

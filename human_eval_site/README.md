# 匿名文本与图片一致性人类测评网页

这是一个面向 DN 项目的评测前端 + 轻量后端。评测者通过邀请链接进入后，会被固定分配到一个游戏主题，只看到匿名的 `方案 A / 方案 B`，不会看到 `ours`、`baseline`、模型名或文件夹名等真实身份信息。

当前版本已经支持：

- 每个主题展示 `5` 段中文剧情
- 每个匿名方案展示对应的连续 `5` 张图片
- 用邀请 token 给不同用户分配不同主题
- 提交后自动回传到本地或服务器端的 Flask 接口
- 同时保留浏览器本地进度和手动导出 JSON/CSV

## 当前本地访问地址

推荐直接启动 Flask 服务：

```bash
cd DN-main
python human_eval_site/server.py
```

然后打开：

```text
http://127.0.0.1:5000/
```

如果是正式邀请链接，则形如：

```text
http://127.0.0.1:5000/?token=YOUR_INVITE_TOKEN
```

## 目录说明

```text
human_eval_site/
  index.html
  styles.css
  app.js
  server.py
  requirements.txt
  data/
    theme_catalog.json
    invite_tokens.json
    invite_links.csv
  assets/
    themes/
  collected_results/
  tools/
    build_theme_catalog.py
    generate_invites.py
```

## 不同用户如何看到不同主题

核心机制不是“用户自己随机抽题”，而是“研究者预先分配主题，再把不同链接发给不同人”。

具体流程如下：

1. `build_theme_catalog.py` 会把现有游戏主题整理成 `theme_catalog.json`
2. `generate_invites.py` 会为每个主题生成多个独立 token
3. 你把不同的邀请链接发给不同评测者
4. 前端通过 `?token=...` 调用 `/api/session`
5. 后端根据 token 返回该用户唯一绑定的主题

这样做的好处是：

- 可以保证不同用户看到的是不同主题
- 可以控制每个主题分配给多少位评测者
- 可以统计哪些 token 已领取、已提交、提交了几次

当前仓库里已经生成了：

- `10` 个主题
- `30` 个邀请 token

如果按每个主题 3 个 token 发送，就可以覆盖 10 个已有主题并收集多位评测者数据。

## 数据内容

正式数据不是旧版的单段文本 + 单张图，而是“1 个主题 = 5 段故事 + 2 组连续 5 图”。

`theme_catalog.json` 中每个主题大致结构如下：

```json
{
  "themeId": "theme_001_game_xxx",
  "case": {
    "storySegments": ["第1段", "第2段", "第3段", "第4段", "第5段"],
    "candidates": [
      {
        "system": "ours",
        "images": [
          "/assets/themes/theme_001_game_xxx/ours/seg_001.png",
          "/assets/themes/theme_001_game_xxx/ours/seg_002.png",
          "/assets/themes/theme_001_game_xxx/ours/seg_003.png",
          "/assets/themes/theme_001_game_xxx/ours/seg_004.png",
          "/assets/themes/theme_001_game_xxx/ours/seg_005.png"
        ]
      },
      {
        "system": "baseline",
        "images": [
          "/assets/themes/theme_001_game_xxx/baseline/seg_001.png",
          "/assets/themes/theme_001_game_xxx/baseline/seg_002.png",
          "/assets/themes/theme_001_game_xxx/baseline/seg_003.png",
          "/assets/themes/theme_001_game_xxx/baseline/seg_004.png",
          "/assets/themes/theme_001_game_xxx/baseline/seg_005.png"
        ]
      }
    ]
  }
}
```

注意：

- 评测界面重点比较的是两组图片与同一组 5 段中文剧情的匹配程度
- `assets/themes/` 已经内置部署所需图片，不再依赖站点外部路径

## 保存与回传

当前版本有三层结果保存：

1. 浏览器 `localStorage` 自动保存评分过程
2. 评测者手动导出本地 `JSON` / `CSV`
3. 提交后自动 `POST /api/submit` 回传到服务器

### 服务器端结果保存位置

后端会把结果写到：

```text
human_eval_site/collected_results/
```

其中包括：

- 每次提交对应的 JSON 文件
- `submissions_index.jsonl` 提交索引
- `latest_submission_summary.json` 最近一次提交摘要

### token 状态记录

后端还会更新：

```text
human_eval_site/data/invite_tokens.json
```

记录以下字段：

- `claimedAt`：这个邀请链接第一次被打开的时间
- `submittedAt`：最近一次提交时间
- `submissionCount`：提交次数
- `evaluatorId`：评测者 ID
- `latestResultFile`：最近一次结果文件路径

## 公网部署

### 现在的真实状态

代码层面已经具备公网部署条件，但当前仓库还没有配置 Git 远端，所以还不能直接完成 Render 这类正式托管平台的上线。

### 推荐方案：Render 部署 Flask 服务

这个项目不只是静态网页，还需要：

- `/api/session` 返回 token 对应主题
- `/api/submit` 自动收集评测结果
- 服务端文件落盘

所以更适合部署为一个完整的 Python Web Service，而不是只放到静态托管平台。

仓库根目录已经可以配合 `render.yaml` 使用。典型流程是：

1. 把当前仓库推到 GitHub / GitLab / Bitbucket
2. 在 Render 中创建 Web Service
3. 构建命令安装 `human_eval_site/requirements.txt`
4. 启动命令运行 `gunicorn`
5. 部署成功后，把 Render 的公网 URL 发给评测者

### 重要提醒

如果你希望“结果文件长期稳定保存在云端磁盘”，要注意：

- 本地运行 Flask：结果会写回你自己电脑
- 云端部署到普通 Web Service：结果写到服务器文件系统
- 如果托管平台文件系统是临时的，重启后可能丢失数据

因此正式长期采集时，推荐：

- 使用带持久磁盘的服务
- 或者把 `/api/submit` 改成写数据库 / 对象存储

## 常用命令

构建主题目录：

```bash
python human_eval_site/tools/build_theme_catalog.py
```

生成邀请链接：

```bash
python human_eval_site/tools/generate_invites.py --raters-per-theme 3
```

启动本地服务：

```bash
python human_eval_site/server.py
```

## 当前结论

从功能上看，下面三项已经完成：

- 不同用户通过不同 token 固定看到不同主题，并能汇总到同一后端
- 每个主题展示 5 段中文剧情和 2 组连续 5 张图片
- 提交后自动回传到本地或服务器端接口并落盘

唯一还没“最终完成”的是正式公网部署地址本身，因为这一步还差 Git 远端和托管平台接入。

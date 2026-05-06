# AutoDL 云端高算力实验环境准备方案

> 任务定位：这不是单纯的软件安装，而是为 DN 后续 baseline、主实验、高配置模型实验准备可复现的云端运行环境，解决本地显卡性能不足导致的实验阻塞。

## 参考来源

- 用户指定教程：<https://blog.csdn.net/qq_44111805/article/details/128416561>
- AutoDL 官方文档入口：<https://www.autodl.com/docs/>
- PyTorch CUDA wheel 安装索引：<https://download.pytorch.org/whl/>

## 目标与边界

### 要解决的问题

1. 本地 GPU 性能不足，无法稳定支撑更高规格模型或更大规模实验。
2. 后续实验需要 GPU、CUDA、PyTorch、项目依赖、环境变量、数据目录、日志目录形成可复用配置。
3. 云端实例必须能快速重建，避免每次开机都从零摸索。

### 本次准备结果

仓库已补充以下云端准备文件：

- `scripts/autodl_bootstrap.sh`：AutoDL 实例初始化脚本。
- `scripts/autodl_smoke_test.py`：依赖、CUDA、GPU、关键环境变量冒烟检查。
- `.env.autodl.template`：云端 `.env` 模板，不包含本地密钥。
- `docs/AUTODL_CLOUD_EXPERIMENT_ENV.md`：本说明文档。

## 推荐 AutoDL 实例配置

### 轻量 baseline / 代码联调

- GPU：RTX 3090 / RTX 4090 级别。
- 显存：24 GB 起。
- 用途：项目迁移验证、API 链路验证、小规模生成或评估。

### 主实验 / 高配置模型

- GPU：A40 / A100 / H100 或同级别。
- 显存：48 GB / 80 GB 优先。
- 用途：更大模型、更大 batch、更长运行时间、多模态或视觉模型链路。

### 镜像建议

优先选择 AutoDL 官方 PyTorch 镜像，满足：

- Ubuntu + CUDA + cuDNN + PyTorch 已预装。
- Python 3.12 可用，或系统带 conda，能创建 Python 3.12 环境。
- JupyterLab / SSH 可用，方便上传代码、运行 notebook、调试服务。

如果镜像只有 Python 3.10/3.11，`scripts/autodl_bootstrap.sh` 会优先尝试用 conda 创建 Python 3.12 环境；如果镜像没有 conda，也没有 Python 3.12，需要换镜像或先安装 Python 3.12。

## AutoDL 平台操作流程

### 1. 创建实例

1. 登录 AutoDL。
2. 选择 GPU 算力规格。
3. 选择 PyTorch/CUDA 镜像。
4. 创建并启动实例。
5. 记录 JupyterLab、SSH、终端入口信息。

### 2. 进入终端

可用以下任一方式：

- AutoDL 控制台网页终端。
- JupyterLab Terminal。
- 本地 SSH 连接。

推荐进入后先确认硬件：

```bash
nvidia-smi
df -h
python --version
conda --version || true
```

### 3. 放置项目代码

AutoDL 通常会提供数据盘路径，例如 `/root/autodl-tmp`。建议把 DN 项目放到数据盘，避免环境和实验产物占用系统盘：

```bash
cd /root/autodl-tmp
```

上传方式二选一：

```bash
# 方式 A：从 Git 仓库拉取
git clone <your-dn-repo-url> DN
cd DN
```

```bash
# 方式 B：本地打包上传后解压
unzip DN.zip -d /root/autodl-tmp
cd /root/autodl-tmp/DN
```

上传时建议排除以下本地缓存或大目录，除非实验必须复用：

- `.venv/`
- `node_modules/`
- `__pycache__/`
- 临时日志、浏览器缓存、无用图片缓存

## 一键初始化 DN 云端环境

在 AutoDL 实例的 DN 项目根目录执行：

```bash
cd /root/autodl-tmp/DN
bash scripts/autodl_bootstrap.sh
```

脚本默认做这些事：

1. 在 `/root/autodl-tmp/envs/dn-cloud` 创建 Python 3.12 环境。
2. 安装 GPU 版 PyTorch、torchvision、torchaudio。
3. 安装 `requirements.txt` 和 `pyproject.toml` 中的项目依赖。
4. 如果没有 `.env`，从 `.env.autodl.template` 创建一份。
5. 运行 `scripts/autodl_smoke_test.py` 检查环境。

后续重新进入实例时激活环境：

```bash
source /root/autodl-tmp/envs/dn-cloud/bin/activate
cd /root/autodl-tmp/DN
```

如需安装评估依赖：

```bash
INSTALL_EVAL=1 bash scripts/autodl_bootstrap.sh
```

如当前 AutoDL 镜像不适配 CUDA 12.8，可指定 PyTorch CUDA wheel 源，例如：

```bash
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124 bash scripts/autodl_bootstrap.sh
```

## 配置 `.env`

初始化后编辑：

```bash
nano .env
```

至少检查这些配置：

```env
Image_Generation_API_KEY=
Image_Generation_BASE_URL=
Image_Generation_MODEL=

Camera_Analyst_API_KEY=
Camera_Analyst_BASE_URL=
Camera_Analyst_MODEL=

COMFYUI_HOST=http://127.0.0.1:8188
ENABLE_MOCK_MODE=false
```

注意：

- 不要把真实 `.env` 提交到 Git。
- 若云端使用外部 API，确认 AutoDL 实例网络可以访问对应 `BASE_URL`。
- 若 ComfyUI 也部署在同一台 AutoDL 实例，`COMFYUI_HOST` 通常可设为 `http://127.0.0.1:8188`。
- 若 ComfyUI 在另一台机器，必须改成可访问的公网或内网地址。

## 冒烟测试

环境安装完成后执行：

```bash
source /root/autodl-tmp/envs/dn-cloud/bin/activate
python scripts/autodl_smoke_test.py
```

期望看到：

- Flask、OpenAI、Google GenAI、OpenCV、Pillow 等依赖导入成功。
- `torch.cuda.is_available()` 为 `True`。
- 输出 GPU 名称。
- CUDA 矩阵乘法 checksum 成功。

如果 CUDA 不可用：

1. 先运行 `nvidia-smi`，确认实例确实分配到 GPU。
2. 查看 `python -c "import torch; print(torch.__version__, torch.version.cuda)"`。
3. 按镜像 CUDA 版本重装 PyTorch wheel。
4. 必要时换 AutoDL 镜像，不建议在不确定驱动版本时强行混装 CUDA。

## 启动 DN 服务

```bash
source /root/autodl-tmp/envs/dn-cloud/bin/activate
cd /root/autodl-tmp/DN
python game_server.py
```

如果服务监听 `127.0.0.1:5001`，可在 AutoDL 中使用端口转发或 JupyterLab 代理访问。若需要外部访问，先确认安全策略，再将 Flask 监听地址改为 `0.0.0.0`。

建议先用 mock 或小样本跑通：

```bash
python test_api.py
python quick_play.py
```

再切换为真实高算力实验配置。

## 实验目录约定

为了让云端实验可追踪，建议统一目录：

```text
/root/autodl-tmp/DN/
  data/                 # 输入数据或样例集
  experiments/          # 实验配置、批量任务配置
  logs/                 # 运行日志
  saves/                # 模型输出、生成结果、checkpoint 或中间产物
```

建议每次正式实验单独建目录：

```text
experiments/
  2026-04-27_autodl_baseline/
    config.json
    run.log
    metrics.json
    notes.md
```

最低限度记录：

- AutoDL GPU 型号和显存。
- 镜像名、Python 版本、PyTorch 版本、CUDA 版本。
- Git commit。
- `.env` 中使用的模型名，但不要记录 API key。
- 输入数据版本。
- 输出目录。

## 高算力实验执行清单

正式跑 baseline、主实验或高配置模型前，逐项确认：

- [ ] AutoDL 实例 GPU 正常，`nvidia-smi` 可见。
- [ ] DN 项目位于 `/root/autodl-tmp/DN` 或其他数据盘目录。
- [ ] 云端 Python 环境已激活。
- [ ] `python scripts/autodl_smoke_test.py` 通过。
- [ ] `.env` 已填入云端可用的模型、API、ComfyUI 配置。
- [ ] 小样本或 mock 路径跑通。
- [ ] 实验输出目录已创建。
- [ ] 日志会写入 `logs/` 或实验专属目录。
- [ ] 长任务已使用 `tmux`、`screen` 或后台进程管理，避免断连中断。

长任务推荐：

```bash
tmux new -s dn-exp
source /root/autodl-tmp/envs/dn-cloud/bin/activate
cd /root/autodl-tmp/DN
python <your_experiment_entry>.py 2>&1 | tee logs/autodl_exp_$(date +%Y%m%d_%H%M%S).log
```

断开后恢复：

```bash
tmux attach -t dn-exp
```

## 常见问题

### 依赖安装慢

默认脚本使用清华 PyPI 镜像：

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

如某些包镜像不同步，可临时换回官方源：

```bash
PIP_INDEX_URL=https://pypi.org/simple bash scripts/autodl_bootstrap.sh
```

### PyTorch CUDA 版本不匹配

先看系统驱动与 CUDA：

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

再按镜像情况指定：

```bash
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124 bash scripts/autodl_bootstrap.sh
```

### 系统盘空间不足

把环境、代码、数据、输出放在 `/root/autodl-tmp`：

```bash
DN_ENV_DIR=/root/autodl-tmp/envs/dn-cloud bash scripts/autodl_bootstrap.sh
```

不要把大模型、图片缓存、视频缓存放在系统盘。

### API 调用失败

检查：

- `.env` 是否已填写。
- `BASE_URL` 是否从 AutoDL 实例可访问。
- API key 是否过期或权限不足。
- 是否需要代理。

## 下一阶段建议

1. 先在 AutoDL 上完成一次小样本 baseline 复现，记录 GPU、耗时、输出质量。
2. 再迁移主实验或更大模型实验。
3. 将每次云端实验输出写入独立目录，便于和本地历史实验比较。
4. 如果某类任务会重复运行，应进一步封装成固定 CLI，例如 `python scripts/run_experiment.py --config experiments/.../config.json`。

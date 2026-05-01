set -euo pipefail
mkdir -p /root/autodl-tmp/baselines/.conda_pkgs /root/autodl-tmp/baselines/logs
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
export CONDA_PKGS_DIRS=/root/autodl-tmp/baselines/.conda_pkgs
if ! conda env list | awk '{print $1}' | grep -qx comfyui; then
  conda create -y -n comfyui python=3.10
fi
conda activate comfyui
export PIP_PROGRESS_BAR=off
python -m pip install --upgrade pip setuptools wheel > /root/autodl-tmp/baselines/logs/comfyui_install.log 2>&1
python -m pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio >> /root/autodl-tmp/baselines/logs/comfyui_install.log 2>&1
python -m pip install -r requirements.txt >> /root/autodl-tmp/baselines/logs/comfyui_install.log 2>&1
python --version
python -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_version', torch.version.cuda)"
python -c "import aiohttp, PIL, safetensors, transformers; import server; print('comfy_import_ok')"
tail -n 60 /root/autodl-tmp/baselines/logs/comfyui_install.log

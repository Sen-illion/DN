set -euo pipefail
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
export PIP_PROGRESS_BAR=off
python -m pip install -r requirements.txt > /root/autodl-tmp/baselines/logs/comfyui_requirements_retry.log 2>&1
python --version
python -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_version', torch.version.cuda)"
python -c "import av, aiohttp, PIL, safetensors, transformers; import server; print('comfy_import_ok')"
tail -n 80 /root/autodl-tmp/baselines/logs/comfyui_requirements_retry.log

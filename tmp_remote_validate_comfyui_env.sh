set -euo pipefail
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
PYTHONPATH=/root/autodl-tmp/baselines/ComfyUI python -c "import server; print('server_ok')"
tail -n 80 /root/autodl-tmp/baselines/logs/comfyui_requirements_retry2.log

set -euo pipefail
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
python main.py --help | head -n 40

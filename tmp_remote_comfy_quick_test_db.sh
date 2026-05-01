set -euo pipefail
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
python main.py --listen 127.0.0.1 --port 8190 --quick-test-for-ci --disable-auto-launch --database-url sqlite:////root/autodl-tmp/baselines/ComfyUI/user/comfyui-quicktest.db

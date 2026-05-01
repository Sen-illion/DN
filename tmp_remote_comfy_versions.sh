set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
python --version
python - <<'PY'
import torch, av, aiohttp, transformers, safetensors
print('torch', torch.__version__, torch.cuda.is_available(), torch.version.cuda)
print('av', av.__version__)
print('aiohttp', aiohttp.__version__)
print('transformers', transformers.__version__)
print('safetensors', safetensors.__version__)
PY

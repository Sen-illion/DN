set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
conda activate storydiffusion
python - <<'PY'
import os
from pathlib import Path
from huggingface_hub import hf_hub_download
repo_id = 'ali-vilab/In-Context-LoRA'
filename = 'movie-shots.safetensors'
local_dir = '/root/autodl-tmp/baselines/ComfyUI/models/loras'
path = Path(local_dir) / filename
print('token_present', bool(os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_HUB_TOKEN')))
print('before_exists', path.exists(), 'size', path.stat().st_size if path.exists() else -1)
out = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir, local_dir_use_symlinks=False)
print('downloaded_path', out)
outp = Path(out)
print('after_exists', outp.exists(), 'size', outp.stat().st_size if outp.exists() else -1)
PY

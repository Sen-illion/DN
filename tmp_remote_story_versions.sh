set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
conda activate storydiffusion
python --version
python - <<'PY'
import torch, diffusers, transformers, xformers, gradio
print('torch', torch.__version__, torch.cuda.is_available(), torch.version.cuda)
print('diffusers', diffusers.__version__)
print('transformers', transformers.__version__)
print('xformers', xformers.__version__)
print('gradio', gradio.__version__)
PY

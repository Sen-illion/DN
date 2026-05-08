#!/usr/bin/env bash
set -euo pipefail

# Remote bootstrap for the AutoDL 4090 baseline machine.
# Run from /root/autodl-tmp/DN after unpacking DN-baselines-lite.tar.gz.

DN_ROOT="${DN_ROOT:-/root/autodl-tmp/DN}"
TMP_ROOT="${TMP_ROOT:-/root/autodl-tmp}"
CONDA_SH="${CONDA_SH:-/root/miniconda3/etc/profile.d/conda.sh}"
HF_CACHE="${HF_CACHE:-/root/autodl-tmp/hf_cache}"

mkdir -p "$TMP_ROOT/hf_cache" "$TMP_ROOT/outputs" "$TMP_ROOT/logs" "$TMP_ROOT/models"

cat > "$TMP_ROOT/env_storydiffusion.sh" <<'EOF'
source /root/miniconda3/etc/profile.d/conda.sh
conda activate storydiffusion
export HF_HOME=/root/autodl-tmp/hf_cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf_cache
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=60
export HF_HUB_ETAG_TIMEOUT=60
export PIP_DEFAULT_TIMEOUT=120
cd /root/autodl-tmp/DN
EOF

cat > "$TMP_ROOT/env_sdmv2.sh" <<'EOF'
source /root/miniconda3/etc/profile.d/conda.sh
conda activate sdmv2
export HF_HOME=/root/autodl-tmp/hf_cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf_cache
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=60
export HF_HUB_ETAG_TIMEOUT=60
export PIP_DEFAULT_TIMEOUT=120
cd /root/autodl-tmp/DN
EOF

cat > "$TMP_ROOT/env_iclora.sh" <<'EOF'
source /root/miniconda3/etc/profile.d/conda.sh
conda activate iclora
export HF_HOME=/root/autodl-tmp/hf_cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf_cache
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=60
export HF_HUB_ETAG_TIMEOUT=60
export PIP_DEFAULT_TIMEOUT=120
cd /root/autodl-tmp/DN
EOF

source "$CONDA_SH"

if ! conda env list | awk '{print $1}' | grep -qx storydiffusion; then
  conda create -n storydiffusion python=3.10 -y
fi
conda activate storydiffusion
python -m pip install -U pip setuptools wheel
python -m pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118
python -m pip install xformers==0.0.20
python -m pip install -r "$DN_ROOT/baselines/StoryDiffusion/requirements.txt"

# Reassert CUDA wheels in case upstream requirements changed torch.
python -m pip install --force-reinstall torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118

python - <<'PY'
import torch
print("torch:", torch.__version__)
print("torch cuda:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
print("gpu count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
PY

echo "StoryDiffusion env ready."
echo "Next command:"
echo "source /root/autodl-tmp/env_storydiffusion.sh"
echo "python scripts/baselines/run_storydiffusion.py --subset baselines/subsets/dn_style_smoke3.json --output /root/autodl-tmp/outputs/storydiffusion_smoke3"

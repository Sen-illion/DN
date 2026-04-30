#!/usr/bin/env bash
set -euo pipefail

TMP_ROOT="${TMP_ROOT:-/root/autodl-tmp}"
DN_ROOT="${DN_ROOT:-/root/autodl-tmp/DN}"
CONDA_SH="${CONDA_SH:-/root/miniconda3/etc/profile.d/conda.sh}"

mkdir -p "$TMP_ROOT/hf_cache" "$TMP_ROOT/outputs" "$TMP_ROOT/logs"

# shellcheck disable=SC1090
source "$CONDA_SH"

if ! conda env list | awk '{print $1}' | grep -qx sdmv2; then
  conda create -n sdmv2 python=3.10 -y
fi

conda activate sdmv2
export HF_HOME="$TMP_ROOT/hf_cache"
export TRANSFORMERS_CACHE="$TMP_ROOT/hf_cache"
export HF_HUB_CACHE="$TMP_ROOT/hf_cache"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=60
export HF_HUB_ETAG_TIMEOUT=60
export PIP_DEFAULT_TIMEOUT=120

python -m pip install -U pip setuptools wheel
python -m pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118
python -m pip install diffusers==0.25.0 transformers==4.36.2 huggingface_hub==0.25.2 "numpy<2" accelerate safetensors scipy pillow

cd "$DN_ROOT"
python - <<'PY'
import os
import torch
import diffusers
import transformers
print("HF_ENDPOINT:", os.environ.get("HF_ENDPOINT"))
print("torch:", torch.__version__)
print("torch cuda:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
print("diffusers:", diffusers.__version__)
print("transformers:", transformers.__version__)
PY

echo "SDM-v2 env ready."

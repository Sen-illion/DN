set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
export PIP_CACHE_DIR=/root/autodl-tmp/baselines/.pip_cache
mkdir -p "$PIP_CACHE_DIR"
python -m pip install --only-binary=:all: --index-url https://pypi.org/simple sentencepiece greenlet
python -c "import sentencepiece, greenlet; print('binary_ok')"

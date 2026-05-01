set -euo pipefail
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
python -m pip install --only-binary=:all: --index-url https://pypi.org/simple av==14.2.0
python -c "import av; print('av', av.__version__)"

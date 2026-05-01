set -euo pipefail
mkdir -p /root/autodl-tmp/baselines/logs /root/autodl-tmp/baselines/.conda_pkgs
cat > /root/autodl-tmp/baselines/logs/comfyui_install_inner.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp/baselines/ComfyUI
source /root/miniconda3/etc/profile.d/conda.sh
export CONDA_PKGS_DIRS=/root/autodl-tmp/baselines/.conda_pkgs
conda activate comfyui
export PIP_PROGRESS_BAR=off
python -m pip install --upgrade pip setuptools wheel
python - <<'PY'
try:
    import torch
    print('preinstalled_torch', torch.__version__, torch.cuda.is_available(), torch.version.cuda)
except Exception as exc:
    print('preinstalled_torch_missing', exc)
PY
python -m pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
python -m pip install -r requirements.txt
python --version
python -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_version', torch.version.cuda)"
python -c "import aiohttp, PIL, safetensors, transformers; import server; print('comfy_import_ok')"
EOF
chmod +x /root/autodl-tmp/baselines/logs/comfyui_install_inner.sh
nohup /root/autodl-tmp/baselines/logs/comfyui_install_inner.sh > /root/autodl-tmp/baselines/logs/comfyui_install_bg.log 2>&1 & echo $! > /root/autodl-tmp/baselines/logs/comfyui_install_bg.pid
sleep 2
printf 'pid=%s\n' "$(cat /root/autodl-tmp/baselines/logs/comfyui_install_bg.pid)"
ps -fp "$(cat /root/autodl-tmp/baselines/logs/comfyui_install_bg.pid)"

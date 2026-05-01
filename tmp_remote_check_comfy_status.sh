source /root/miniconda3/etc/profile.d/conda.sh
conda env list
if conda env list | awk '{print $1}' | grep -qx comfyui; then
  conda activate comfyui
  python --version
  python -c "import torch; print('torch', torch.__version__, torch.cuda.is_available(), torch.version.cuda)" 2>/dev/null || true
  python -c "import server; print('server_ok')" 2>/dev/null || true
fi
ls -lh /root/autodl-tmp/baselines/logs/comfyui_install.log 2>/dev/null || true
tail -n 60 /root/autodl-tmp/baselines/logs/comfyui_install.log 2>/dev/null || true

set +e
source /root/miniconda3/etc/profile.d/conda.sh
conda activate comfyui
python -c "import torch; print('torch', torch.__version__, torch.cuda.is_available(), torch.version.cuda)" 2>/dev/null || true
python -c "import av; print('av', av.__version__)" 2>/dev/null || true
python -c "import server; print('server_ok')" 2>/dev/null || true
ls -lh /root/autodl-tmp/baselines/logs/comfyui_requirements_retry.log 2>/dev/null || true
tail -n 120 /root/autodl-tmp/baselines/logs/comfyui_requirements_retry.log 2>/dev/null || true

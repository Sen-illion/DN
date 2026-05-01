set +u
cd /root/autodl-tmp/baselines
printf 'host=%s\n' "$(hostname)"
printf 'pwd=%s\n' "$(pwd)"
which python || true
/root/miniconda3/bin/conda env list || true
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
source /root/miniconda3/etc/profile.d/conda.sh
if conda env list | awk '{print $1}' | grep -qx storydiffusion; then
  conda activate storydiffusion
  echo '[storydiffusion]'
  python --version
  python -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_version', torch.version.cuda)"
  python -c "import diffusers, transformers, xformers, gradio; print('imports ok')"
fi
cd /root/autodl-tmp/baselines/ComfyUI 2>/dev/null || true
printf 'comfyui_dir=%s\n' "$(pwd)"
ls -1 models 2>/dev/null || true
for f in \
  models/unet/flux1-dev.safetensors \
  models/vae/ae.safetensors \
  models/clip/t5xxl_fp8_e4m3fn.safetensors \
  models/clip/t5xxl_fp16.safetensors \
  models/clip/clip_l.safetensors \
  models/loras/movie-shots.safetensors; do
  if [ -f "$f" ]; then
    printf 'FOUND %s %s\n' "$f" "$(du -h "$f" | cut -f1)"
  else
    printf 'MISSING %s\n' "$f"
  fi
done

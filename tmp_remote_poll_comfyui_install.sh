set +e
PID=$(cat /root/autodl-tmp/baselines/logs/comfyui_install_bg.pid 2>/dev/null)
echo "pid=$PID"
if [ -n "$PID" ]; then
  ps -fp "$PID" || true
fi
tail -n 80 /root/autodl-tmp/baselines/logs/comfyui_install_bg.log 2>/dev/null || true

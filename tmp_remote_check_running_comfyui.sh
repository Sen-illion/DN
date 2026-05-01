set +e
PID=16715
readlink -f /proc/$PID/cwd || true
tr '\0' ' ' < /proc/$PID/cmdline || true
echo
curl -I --max-time 10 http://127.0.0.1:8188/ || true
curl --max-time 10 http://127.0.0.1:8188/system_stats || true

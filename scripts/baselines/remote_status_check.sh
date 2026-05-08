#!/usr/bin/env bash
set -euo pipefail

TMP_ROOT="${TMP_ROOT:-/root/autodl-tmp}"

echo "=== time ==="
date

echo "=== processes ==="
ps -ef | grep -E 'run_storydiffusion|run_sdmv2|run_iclora|python scripts/baselines' | grep -v grep || true

echo "=== gpu ==="
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader || nvidia-smi || true

echo "=== conda envs ==="
if [ -f /root/miniconda3/etc/profile.d/conda.sh ]; then
  # shellcheck disable=SC1091
  source /root/miniconda3/etc/profile.d/conda.sh
  conda env list || true
fi

echo "=== latest logs ==="
find "$TMP_ROOT/logs" -maxdepth 1 -type f -name '*.log' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' 2>/dev/null | sort | tail -20 || true

echo "=== latest StoryDiffusion log tail ==="
latest_story="$(ls -t "$TMP_ROOT"/logs/storydiffusion_*.log "$TMP_ROOT"/logs/storydiffusion_smoke3_*.log 2>/dev/null | head -1 || true)"
if [ -n "$latest_story" ]; then
  echo "$latest_story"
  tail -n 160 "$latest_story" || true
else
  echo "NO_STORYDIFFUSION_LOG"
fi

echo "=== output metrics ==="
find "$TMP_ROOT/outputs" -name metrics.json -type f 2>/dev/null -print -exec cat {} \; || true

echo "=== output files tail ==="
find "$TMP_ROOT/outputs" -maxdepth 5 -type f 2>/dev/null | sort | tail -160 || true

echo "=== disk ==="
df -h / "$TMP_ROOT" /autodl-pub/data 2>/dev/null || true

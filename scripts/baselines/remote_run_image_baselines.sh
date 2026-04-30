#!/usr/bin/env bash
set -euo pipefail

TMP_ROOT="${TMP_ROOT:-/root/autodl-tmp}"
DN_ROOT="${DN_ROOT:-/root/autodl-tmp/DN}"
STAMP="${RUN_STAMP:-$(date +%Y%m%d_%H%M%S)}"

cd "$DN_ROOT"
mkdir -p "$TMP_ROOT/logs" "$TMP_ROOT/outputs"

run_story_smoke() {
  # shellcheck disable=SC1091
  source "$TMP_ROOT/env_storydiffusion.sh"
  python scripts/baselines/run_storydiffusion.py \
    --subset baselines/subsets/dn_style_smoke3.json \
    --output "$TMP_ROOT/outputs/storydiffusion_smoke3" \
    --run-id "smoke3_${STAMP}" \
    --sd-type SDXL \
    --steps "${STORY_STEPS:-20}" \
    --scene-count 4
}

run_story_formal() {
  # shellcheck disable=SC1091
  source "$TMP_ROOT/env_storydiffusion.sh"
  python scripts/baselines/run_storydiffusion.py \
    --subset baselines/subsets/dn_style_formal8.json \
    --output "$TMP_ROOT/outputs/storydiffusion_formal8" \
    --run-id "formal8_${STAMP}" \
    --sd-type SDXL \
    --steps "${STORY_STEPS:-20}" \
    --scene-count 4
}

run_sdm_smoke() {
  # shellcheck disable=SC1091
  source "$TMP_ROOT/env_sdmv2.sh"
  python scripts/baselines/run_sdmv2.py \
    --subset baselines/subsets/dn_style_smoke3.json \
    --output "$TMP_ROOT/outputs/sdmv2_smoke3" \
    --run-id "smoke3_${STAMP}" \
    --steps "${SDMV2_STEPS:-25}" \
    --scene-count 4
}

run_sdm_formal() {
  # shellcheck disable=SC1091
  source "$TMP_ROOT/env_sdmv2.sh"
  python scripts/baselines/run_sdmv2.py \
    --subset baselines/subsets/dn_style_formal8.json \
    --output "$TMP_ROOT/outputs/sdmv2_formal8" \
    --run-id "formal8_${STAMP}" \
    --steps "${SDMV2_STEPS:-25}" \
    --scene-count 4
}

case "${1:-all}" in
  story-smoke) run_story_smoke 2>&1 | tee "$TMP_ROOT/logs/storydiffusion_smoke3_${STAMP}.log" ;;
  story-formal) run_story_formal 2>&1 | tee "$TMP_ROOT/logs/storydiffusion_formal8_${STAMP}.log" ;;
  sdm-smoke) run_sdm_smoke 2>&1 | tee "$TMP_ROOT/logs/sdmv2_smoke3_${STAMP}.log" ;;
  sdm-formal) run_sdm_formal 2>&1 | tee "$TMP_ROOT/logs/sdmv2_formal8_${STAMP}.log" ;;
  all)
    run_story_smoke 2>&1 | tee "$TMP_ROOT/logs/storydiffusion_smoke3_${STAMP}.log"
    run_story_formal 2>&1 | tee "$TMP_ROOT/logs/storydiffusion_formal8_${STAMP}.log"
    run_sdm_smoke 2>&1 | tee "$TMP_ROOT/logs/sdmv2_smoke3_${STAMP}.log"
    run_sdm_formal 2>&1 | tee "$TMP_ROOT/logs/sdmv2_formal8_${STAMP}.log"
    ;;
  *)
    echo "Usage: $0 [story-smoke|story-formal|sdm-smoke|sdm-formal|all]" >&2
    exit 2
    ;;
esac

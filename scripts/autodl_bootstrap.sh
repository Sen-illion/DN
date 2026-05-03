#!/usr/bin/env bash
set -euo pipefail

# DN AutoDL bootstrap. Run from the project root after uploading/cloning this repo.

PROJECT_DIR="${DN_PROJECT_DIR:-$(pwd)}"
ENV_DIR="${DN_ENV_DIR:-/root/autodl-tmp/envs/dn-cloud}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
INSTALL_TORCH="${INSTALL_TORCH:-1}"
INSTALL_EVAL="${INSTALL_EVAL:-0}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

if [[ ! -f "${PROJECT_DIR}/pyproject.toml" && ! -f "${PROJECT_DIR}/requirements.txt" ]]; then
  echo "ERROR: ${PROJECT_DIR} does not look like the DN project root." >&2
  echo "Run this script from the uploaded/cloned DN repository, or set DN_PROJECT_DIR." >&2
  exit 1
fi

mkdir -p "$(dirname "${ENV_DIR}")"

echo "== DN AutoDL bootstrap =="
echo "Project: ${PROJECT_DIR}"
echo "Env:     ${ENV_DIR}"

if [[ -x "${ENV_DIR}/bin/python" ]]; then
  echo "Existing environment found."
else
  if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    "${PYTHON_BIN}" -m venv "${ENV_DIR}"
  elif command -v conda >/dev/null 2>&1; then
    conda create -y -p "${ENV_DIR}" python=3.12
  else
    echo "ERROR: Python 3.12 or conda is required. Choose an AutoDL PyTorch image with Python 3.12, or install Python 3.12 first." >&2
    exit 1
  fi
fi

source "${ENV_DIR}/bin/activate"
python -m pip install --upgrade pip setuptools wheel

if [[ "${INSTALL_TORCH}" == "1" ]]; then
  echo "Installing GPU PyTorch stack from ${TORCH_INDEX_URL}"
  python -m pip install --upgrade torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}"
fi

echo "Installing DN runtime dependencies"
python -m pip install -r "${PROJECT_DIR}/requirements.txt" -i "${PIP_INDEX_URL}"

if [[ -f "${PROJECT_DIR}/pyproject.toml" ]]; then
  python -m pip install -e "${PROJECT_DIR}" -i "${PIP_INDEX_URL}"
fi

if [[ "${INSTALL_EVAL}" == "1" && -f "${PROJECT_DIR}/requirements-eval.txt" ]]; then
  echo "Installing optional evaluation dependencies"
  python -m pip install -r "${PROJECT_DIR}/requirements-eval.txt" -i "${PIP_INDEX_URL}"
fi

if [[ ! -f "${PROJECT_DIR}/.env" && -f "${PROJECT_DIR}/.env.autodl.template" ]]; then
  cp "${PROJECT_DIR}/.env.autodl.template" "${PROJECT_DIR}/.env"
  echo "Created ${PROJECT_DIR}/.env from .env.autodl.template. Fill API keys before running real experiments."
fi

python "${PROJECT_DIR}/scripts/autodl_smoke_test.py"

cat <<EOF

Bootstrap finished.
Activate later with:
  source ${ENV_DIR}/bin/activate

Run the local web workflow on AutoDL with:
  cd ${PROJECT_DIR}
  python game_server.py

For evaluation dependencies, rerun with:
  INSTALL_EVAL=1 bash scripts/autodl_bootstrap.sh
EOF

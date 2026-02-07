#!/usr/bin/env bash
# Usage: ./setup_env.sh
# Creates a .venv directory (if missing), activates it, upgrades pip and installs requirements.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.8+ and re-run."
  exit 1
fi

PY_CMD=python3
if ! command -v python3 >/dev/null 2>&1; then
  PY_CMD=python
fi

if [ ! -d "$VENV_DIR" ]; then
  "$PY_CMD" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r "$ROOT_DIR/requirements.txt"

echo "Environment ready. To activate: source .venv/bin/activate"

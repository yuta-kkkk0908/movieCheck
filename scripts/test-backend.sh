#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$PROJECT_ROOT/backend"

if command -v python3 >/dev/null 2>&1; then
  BASE_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  BASE_PYTHON="python"
else
  echo "python/python3 が見つかりません。Python をインストールしてください。" >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "backend/.venv を作成します..."
  "$BASE_PYTHON" -m venv .venv
fi

PYTHON_BIN=".venv/bin/python"
PIP_BIN=".venv/bin/pip"

if ! "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
  echo "テスト依存を backend/.venv にインストールします..."
  "$PIP_BIN" install -r requirements.txt
fi

if [ "$#" -gt 0 ]; then
  "$PYTHON_BIN" -m pytest "$@"
else
  "$PYTHON_BIN" -m pytest -q
fi

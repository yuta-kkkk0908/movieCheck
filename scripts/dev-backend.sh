#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd backend

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

if ! "$PYTHON_BIN" -c "import bs4, fastapi, sqlalchemy" >/dev/null 2>&1; then
  echo "バックエンド依存を backend/.venv にインストールします..."
  "$PIP_BIN" install -r requirements.txt
fi

"$PYTHON_BIN" main.py

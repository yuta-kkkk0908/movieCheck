#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$PROJECT_ROOT/frontend"

if [ ! -x "./node_modules/.bin/react-scripts" ]; then
  echo "[INFO] frontend 依存が見つからないため npm install を実行します..."
  npm install
fi

# WSL + Windowsパス環境での一時ディレクトリ権限エラーを回避
if [ -z "${TMPDIR:-}" ]; then
  export TMPDIR="/tmp"
fi

# CIモードでwatchを抑止し、ローカルでも1回で終了させる
if [ -z "${CI:-}" ]; then
  export CI=1
fi

if [ "$#" -gt 0 ]; then
  npm test -- "$@"
else
  npm test -- --watchAll=false --passWithNoTests
fi

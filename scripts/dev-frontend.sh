#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$PROJECT_ROOT"

if [[ "$(pwd)" == /mnt/* ]]; then
  echo "[WARN] /mnt 配下での npm start は初回コンパイルが遅くなりやすいです。"
  echo "[WARN] 高速化するには WSL 側パス（例: ~/projects）へプロジェクトを移動してください。"
fi

cd "$PROJECT_ROOT/frontend"

if [ ! -x "./node_modules/.bin/react-scripts" ]; then
  echo "[INFO] frontend 依存が見つからないため npm install を実行します..."
  npm install
fi

# 開発起動の初回コンパイルを軽くする
export DISABLE_ESLINT_PLUGIN=true
export BROWSER=none
export FAST_REFRESH=false
export CHOKIDAR_USEPOLLING=false
export WATCHPACK_POLLING=false
export HOST=127.0.0.1

npm start

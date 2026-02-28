#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-all}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/test-all.sh                 # backend + frontend
  ./scripts/test-all.sh backend [args] # backendのみ
  ./scripts/test-all.sh frontend [args]# frontendのみ
EOF
}

case "$TARGET" in
  all)
    if [ "$#" -gt 1 ]; then
      echo "all指定時は追加引数を受け付けません。" >&2
      usage
      exit 1
    fi
    "$SCRIPT_DIR/test-backend.sh"
    "$SCRIPT_DIR/test-frontend.sh"
    ;;
  backend)
    shift
    "$SCRIPT_DIR/test-backend.sh" "$@"
    ;;
  frontend)
    shift
    "$SCRIPT_DIR/test-frontend.sh" "$@"
    ;;
  *)
    echo "不正なターゲット: $TARGET" >&2
    usage
    exit 1
    ;;
esac

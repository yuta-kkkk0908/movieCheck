#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
trap 'kill 0' INT TERM EXIT
(cd backend && python main.py) &
(cd frontend && npm start) &
wait

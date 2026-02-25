#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd backend
python -m pytest -q

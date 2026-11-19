#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "[ERROR] .venv not found. Create it with: uv venv --python 3.12 .venv && uv pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "frontend/dist/index.html" ] && command -v npm >/dev/null 2>&1; then
  echo "[ShortsFactory] Building frontend bundle..."
  (cd frontend && npm install && npm run build)
fi

echo "[ShortsFactory] Starting server on http://127.0.0.1:8000 ..."
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

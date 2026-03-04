#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

pip install -q fastapi uvicorn pydantic websockets httpx >/dev/null 2>&1 || true

pkill -f "uvicorn backend.app:app" || true
pkill -f "http.server 9000" || true

nohup uvicorn backend.app:app --host 0.0.0.0 --port 8080 > /tmp/freecad_mcp_backend.log 2>&1 < /dev/null &
echo $! > /tmp/freecad_mcp_backend.pid

nohup python3 -m http.server 9000 -d client --bind 0.0.0.0 > /tmp/freecad_mcp_client.log 2>&1 < /dev/null &
echo $! > /tmp/freecad_mcp_client.pid

sleep 1

echo "Started."
echo "Backend PID: $(cat /tmp/freecad_mcp_backend.pid)"
echo "Client PID:  $(cat /tmp/freecad_mcp_client.pid)"

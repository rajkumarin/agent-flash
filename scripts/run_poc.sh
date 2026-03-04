#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "[1/4] Installing POC deps"
pip install -q fastapi uvicorn pydantic websockets httpx

echo "[2/4] Starting backend on :8080"
uvicorn backend.app:app --host 0.0.0.0 --port 8080 > /tmp/freecad_mcp_backend.log 2>&1 &
BACK_PID=$!

sleep 2

echo "[3/4] Running smoke test"
python backend/smoke_test.py

echo "[4/4] Starting static client on :9000 (IPv4)"
python -m http.server 9000 -d client --bind 0.0.0.0 > /tmp/freecad_mcp_client.log 2>&1 &
CLIENT_PID=$!

cat <<MSG
POC started successfully.
- Backend: http://localhost:8080/health
- Client:  http://localhost:9000
- Tablet URL: http://<LAPTOP_IP>:9000

Stop with:
  kill $BACK_PID $CLIENT_PID
MSG

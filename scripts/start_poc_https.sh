#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

pip install -q fastapi uvicorn pydantic websockets httpx >/dev/null 2>&1 || true

mkdir -p certs
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)"
if [[ ! -f certs/dev-cert.pem || ! -f certs/dev-key.pem ]]; then
  openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
    -keyout certs/dev-key.pem \
    -out certs/dev-cert.pem \
    -subj "/CN=localhost" \
    -addext "subjectAltName=IP:127.0.0.1,IP:${LAN_IP},DNS:localhost" >/dev/null 2>&1 || true
fi

pkill -f "uvicorn backend.app:app" || true
pkill -f "http.server 9000" || true

nohup uvicorn backend.app:app \
  --host 0.0.0.0 --port 8443 \
  --ssl-keyfile certs/dev-key.pem \
  --ssl-certfile certs/dev-cert.pem \
  > /tmp/freecad_mcp_backend_https.log 2>&1 < /dev/null &

echo $! > /tmp/freecad_mcp_backend_https.pid
sleep 1

echo "HTTPS backend started."
echo "PID: $(cat /tmp/freecad_mcp_backend_https.pid)"
echo "Open on tablet: https://${LAN_IP}:8443/index.html?v=3"

#!/usr/bin/env bash
set -euo pipefail

echo "=== LISTENERS ==="
lsof -nP -iTCP:8080 -sTCP:LISTEN || true
lsof -nP -iTCP:9000 -sTCP:LISTEN || true
lsof -nP -iTCP:8443 -sTCP:LISTEN || true

echo "=== HEALTH ==="
curl -sS http://127.0.0.1:8080/health || true
echo
curl -sSI http://127.0.0.1:9000 | head -n 1 || true
curl -ksS https://127.0.0.1:8443/health || true
echo
curl -ksSI https://127.0.0.1:8443/ | head -n 1 || true

echo "=== PID FILES ==="
[[ -f /tmp/freecad_mcp_backend.pid ]] && echo "backend pid: $(cat /tmp/freecad_mcp_backend.pid)" || echo "backend pid file missing"
[[ -f /tmp/freecad_mcp_client.pid ]] && echo "client pid:  $(cat /tmp/freecad_mcp_client.pid)" || echo "client pid file missing"
[[ -f /tmp/freecad_mcp_backend_https.pid ]] && echo "https backend pid: $(cat /tmp/freecad_mcp_backend_https.pid)" || echo "https backend pid file missing"

#!/usr/bin/env bash
set -euo pipefail

echo "=== LISTENER ==="
lsof -nP -iTCP:8443 -sTCP:LISTEN || true

echo "=== HTTPS HEALTH (insecure cert accept) ==="
curl -ksS https://127.0.0.1:8443/health || true
echo
curl -ksSI https://127.0.0.1:8443/ | head -n 1 || true

echo "=== PID FILE ==="
[[ -f /tmp/freecad_mcp_backend_https.pid ]] && echo "https backend pid: $(cat /tmp/freecad_mcp_backend_https.pid)" || echo "pid file missing"

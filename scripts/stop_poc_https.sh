#!/usr/bin/env bash
set -euo pipefail

if [[ -f /tmp/freecad_mcp_backend_https.pid ]]; then
  kill "$(cat /tmp/freecad_mcp_backend_https.pid)" 2>/dev/null || true
  rm -f /tmp/freecad_mcp_backend_https.pid
fi
pkill -f "uvicorn backend.app:app" || true

echo "HTTPS backend stopped."

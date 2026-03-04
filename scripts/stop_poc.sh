#!/usr/bin/env bash
set -euo pipefail

if [[ -f /tmp/freecad_mcp_backend.pid ]]; then
  kill "$(cat /tmp/freecad_mcp_backend.pid)" 2>/dev/null || true
  rm -f /tmp/freecad_mcp_backend.pid
fi
if [[ -f /tmp/freecad_mcp_client.pid ]]; then
  kill "$(cat /tmp/freecad_mcp_client.pid)" 2>/dev/null || true
  rm -f /tmp/freecad_mcp_client.pid
fi
pkill -f "uvicorn backend.app:app" || true
pkill -f "http.server 9000" || true

echo "Stopped."

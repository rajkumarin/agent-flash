# Backend (Camera Overlay PoC)

## Run (HTTP mode)

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload
```

Health check:

```bash
curl http://localhost:8080/health
```

WebSocket endpoint:

- `ws://<laptop-ip>:8080/ws/session`

## Run (HTTPS mode for Android camera)

Use script (recommended):

```bash
scripts/start_poc_https.sh
scripts/status_poc_https.sh
```

Open on tablet:

- `https://<laptop-ip>:8443/index.html?v=3`

Notes:
- HTTPS mode serves static client and backend from the same origin.
- WebSocket auto-switches to `wss://` in client code when loaded via HTTPS.

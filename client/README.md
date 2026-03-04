# Client (Tablet Camera Thin Client)

## Recommended (Android Chrome camera)

Use HTTPS backend mode:

```bash
scripts/start_poc_https.sh
scripts/status_poc_https.sh
```

Open:

- `https://<laptop-ip>:8443/index.html?v=3`

Then accept the self-signed cert warning once.

## Legacy HTTP mode (debug only)

Serve this folder with any static server:

```bash
python -m http.server 9000 -d client
```

Open on tablet browser:

- `http://<laptop-ip>:9000`

Steps:
1. Click `Start Camera` and allow camera permissions.
2. Set backend WebSocket URL if needed (`ws://<laptop-ip>:8080/ws/session`).
3. Click `Connect Backend`.

## Troubleshooting

- If camera fails with insecure-context error on Android, use HTTPS mode above.
- If buttons look unresponsive, check on-screen debug console (`Boot...`, click events, socket status).

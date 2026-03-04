"""Backend smoke test for camera overlay websocket contract."""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import websockets


async def test_ws() -> None:
    uri = "ws://127.0.0.1:8080/ws/session"
    async with websockets.connect(uri, max_size=2_000_000) as ws:
        payload = {
            "type": "frame",
            "ts": int(time.time() * 1000),
            "jpeg_base64": "",
            "width": 640,
            "height": 360,
        }
        await ws.send(json.dumps(payload))
        m1 = json.loads(await ws.recv())
        m2 = json.loads(await ws.recv())

    msgs = {m1.get("type"): m1, m2.get("type"): m2}
    overlay = msgs.get("overlay")
    status = msgs.get("status")

    assert overlay, "overlay message missing"
    assert status, "status message missing"
    assert overlay["top_k"] == 5, "top_k must be 5"
    assert len(overlay["parts"]) == 5, "parts length must be 5"

    for part in overlay["parts"]:
        assert 0.0 <= part["conf"] <= 1.0
        for key in ("x", "y", "w", "h"):
            assert 0.0 <= part["bbox"][key] <= 1.0


def test_health() -> None:
    r = httpx.get("http://127.0.0.1:8080/health", timeout=5.0)
    r.raise_for_status()
    data = r.json()
    assert data.get("ok") is True
    assert data.get("service") == "camera-overlay-backend"


if __name__ == "__main__":
    test_health()
    asyncio.run(test_ws())
    print("SMOKE_TEST_OK")

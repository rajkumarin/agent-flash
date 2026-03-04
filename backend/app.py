"""Local backend for tablet camera overlay PoC."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .inference import ExponentialSmoothingTracker, MockPartDetector
from .schemas import FrameMessage, OverlayMessage, StatusMessage

app = FastAPI(title="LEGO Camera Overlay Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_detector = MockPartDetector()
_tracker = ExponentialSmoothingTracker(alpha=0.45)
_frame_times = deque(maxlen=60)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "camera-overlay-backend", "model": _detector.model_name}


@app.websocket("/ws/session")
async def ws_session(ws: WebSocket) -> None:
    await ws.accept()

    try:
        while True:
            raw = await ws.receive_json()
            frame = FrameMessage.model_validate(raw)

            now = time.time()
            _frame_times.append(now)

            predictions = _detector.predict_top_k(
                frame=frame.jpeg_base64,
                width=frame.width,
                height=frame.height,
                k=5,
            )
            predictions = _tracker.update(predictions)

            overlay = OverlayMessage(ts=frame.ts, top_k=5, parts=list(predictions))
            await ws.send_json(overlay.model_dump())

            fps = _calculate_fps()
            latency_ms = max(0.0, (time.time() * 1000.0) - frame.ts)
            status = StatusMessage(fps=fps, latency_ms=latency_ms, model_name=_detector.model_name)
            await ws.send_json(status.model_dump())

    except WebSocketDisconnect:
        return


def _calculate_fps() -> float:
    if len(_frame_times) < 2:
        return 0.0
    elapsed = _frame_times[-1] - _frame_times[0]
    if elapsed <= 0:
        return 0.0
    return (len(_frame_times) - 1) / elapsed


# Serve thin-client assets from the backend so HTTPS and WSS are same-origin.
_client_dir = Path(__file__).resolve().parent.parent / "client"
app.mount("/", StaticFiles(directory=str(_client_dir), html=True), name="client")

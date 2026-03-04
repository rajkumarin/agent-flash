"""Data contracts for camera overlay WebSocket messages."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Axis-aligned bounding box in normalized coordinates [0,1]."""

    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., ge=0.0, le=1.0)
    h: float = Field(..., ge=0.0, le=1.0)


class Anchor(BaseModel):
    """Anchor point for label placement in normalized coordinates [0,1]."""

    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class PartPrediction(BaseModel):
    """Single part hypothesis."""

    part_id: str
    label: str
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: BBox
    anchor: Anchor


class FrameMessage(BaseModel):
    """Incoming camera frame event from thin client."""

    type: str = "frame"
    ts: int
    jpeg_base64: Optional[str] = None
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class OverlayMessage(BaseModel):
    """Outgoing overlay message for rendering in thin client."""

    type: str = "overlay"
    ts: int
    top_k: int = 5
    parts: List[PartPrediction]


class StatusMessage(BaseModel):
    """Outgoing status telemetry."""

    type: str = "status"
    fps: float
    latency_ms: float
    model_name: str

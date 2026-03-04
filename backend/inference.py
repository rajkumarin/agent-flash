"""POC inference components: mock part detector + lightweight tracker."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from .providers import PartDetector, Tracker
from .schemas import Anchor, BBox, PartPrediction


_PART_CATALOG = [
    ("part_wheel_front_left", "Front Left Wheel"),
    ("part_wheel_front_right", "Front Right Wheel"),
    ("part_wheel_rear_left", "Rear Left Wheel"),
    ("part_wheel_rear_right", "Rear Right Wheel"),
    ("part_blade", "Front Blade"),
    ("part_cabin", "Cabin Frame"),
    ("part_exhaust", "Exhaust Pipe"),
    ("part_track_left", "Left Track Assembly"),
    ("part_track_right", "Right Track Assembly"),
    ("part_lift_arm", "Lift Arm"),
]


class MockPartDetector(PartDetector):
    """Return plausible top-k part predictions for end-to-end wiring tests."""

    model_name = "mock-part-detector-v1"

    def predict_top_k(self, frame, width: int, height: int, k: int = 5) -> Sequence[PartPrediction]:
        del frame, width, height
        choices = random.sample(_PART_CATALOG, k=min(k, len(_PART_CATALOG)))
        predictions: list[PartPrediction] = []

        for idx, (part_id, label) in enumerate(choices):
            x = 0.12 + (idx * 0.15) + random.uniform(-0.03, 0.03)
            y = 0.2 + random.uniform(-0.06, 0.06)
            w = 0.14 + random.uniform(-0.03, 0.03)
            h = 0.1 + random.uniform(-0.02, 0.02)
            conf = max(0.1, min(0.99, 0.92 - idx * 0.1 + random.uniform(-0.04, 0.04)))

            bbox = BBox(
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                w=max(0.05, min(0.3, w)),
                h=max(0.04, min(0.25, h)),
            )
            anchor = Anchor(x=min(1.0, bbox.x + bbox.w / 2), y=max(0.0, bbox.y - 0.01))
            predictions.append(
                PartPrediction(part_id=part_id, label=label, conf=conf, bbox=bbox, anchor=anchor)
            )

        predictions.sort(key=lambda p: p.conf, reverse=True)
        return predictions[:k]


@dataclass
class _TrackState:
    x: float
    y: float
    conf: float


class ExponentialSmoothingTracker(Tracker):
    """Simple label stabilization for PoC without object identity complexity."""

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self._state: dict[str, _TrackState] = {}

    def update(self, predictions: Sequence[PartPrediction]) -> Sequence[PartPrediction]:
        smoothed: list[PartPrediction] = []

        for pred in predictions:
            prev = self._state.get(pred.part_id)
            if prev is None:
                self._state[pred.part_id] = _TrackState(pred.anchor.x, pred.anchor.y, pred.conf)
                smoothed.append(pred)
                continue

            new_x = self.alpha * pred.anchor.x + (1 - self.alpha) * prev.x
            new_y = self.alpha * pred.anchor.y + (1 - self.alpha) * prev.y
            new_conf = self.alpha * pred.conf + (1 - self.alpha) * prev.conf

            self._state[pred.part_id] = _TrackState(new_x, new_y, new_conf)
            smoothed.append(
                PartPrediction(
                    part_id=pred.part_id,
                    label=pred.label,
                    conf=new_conf,
                    bbox=pred.bbox,
                    anchor=Anchor(x=new_x, y=new_y),
                )
            )

        return smoothed

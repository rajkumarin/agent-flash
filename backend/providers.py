"""Future-ready interfaces for CV, VLM, and LLM components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from .schemas import PartPrediction


class PartDetector(ABC):
    """Detect or classify visible parts from camera frames."""

    @abstractmethod
    def predict_top_k(self, frame: Any, width: int, height: int, k: int = 5) -> Sequence[PartPrediction]:
        raise NotImplementedError


class Tracker(ABC):
    """Smooth predictions across frames."""

    @abstractmethod
    def update(self, predictions: Sequence[PartPrediction]) -> Sequence[PartPrediction]:
        raise NotImplementedError


class VisionReasoner(ABC):
    """Optional VLM path for ambiguity resolution."""

    @abstractmethod
    def resolve(self, frame: Any, candidates: Sequence[PartPrediction]) -> Sequence[PartPrediction]:
        raise NotImplementedError


class ReasoningProvider(ABC):
    """Future LLM reasoning provider for repair instructions."""

    @abstractmethod
    def generate_repair_instructions(self, context: dict[str, Any]) -> str:
        raise NotImplementedError

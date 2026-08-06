from dataclasses import dataclass
from typing import Any


@dataclass
class PoseResult:
    """
    Standard result returned by a future pose engine.
    """

    landmarks: list[dict[str, Any]]
    frame_count: int
    confidence: float
    metadata: dict[str, Any]


class PoseEngine:
    """
    Base interface for pose-detection implementations.

    A future MediaPipe engine should return the same
    PoseResult structure.
    """

    def analyze(
        self,
        video_path: str,
    ) -> PoseResult:
        raise NotImplementedError(
            'A real pose engine has not been connected yet.'
        )
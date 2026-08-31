from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
import numpy as np


@dataclass(slots=True)
class NormalizedFrame:
    """Normalized video frame produced by all VideoSource implementations."""
    camera_id: str
    frame_id: int
    timestamp: datetime
    frame: np.ndarray  # OpenCV BGR uint8 image array

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

    @property
    def shape(self) -> Tuple[int, int, int]:
        return self.frame.shape

    @property
    def height(self) -> int:
        return self.frame.shape[0]

    @property
    def width(self) -> int:
        return self.frame.shape[1]


class VideoSource:
    """Abstract base class for all source-agnostic video input sources."""

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.frame_count = 0

    def read(self) -> Tuple[bool, Optional[NormalizedFrame]]:
        """Read the next normalized frame. Returns (success, NormalizedFrame)."""
        raise NotImplementedError("Subclasses must implement read()")

    def is_open(self) -> bool:
        """Check if video source is active and connected."""
        raise NotImplementedError("Subclasses must implement is_open()")

    def release(self) -> None:
        """Release underlying video capture resources."""
        raise NotImplementedError("Subclasses must implement release()")

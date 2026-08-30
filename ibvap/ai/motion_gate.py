"""Lightweight motion gate for smartphone CCTV streams.

The gate deliberately contains no model-runtime dependency. It decides whether
expensive face/ANPR inference should run and keeps the models awake briefly after
motion stops so that useful evidence is not lost between frames.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class MotionDecision:
    awake: bool
    motion_ratio: float
    reason: str
    hold_frames_remaining: int


class MotionGate:
    """Detect meaningful frame-to-frame change on a small grayscale image."""

    def __init__(
        self,
        min_motion_ratio: float = 0.03,
        pixel_difference_threshold: int = 25,
        hold_frames: int = 20,
        analysis_width: int = 320,
    ) -> None:
        if not 0.0 <= min_motion_ratio <= 1.0:
            raise ValueError("min_motion_ratio must be between 0 and 1")
        if not 0 <= pixel_difference_threshold <= 255:
            raise ValueError("pixel_difference_threshold must be between 0 and 255")
        if hold_frames < 0 or analysis_width < 1:
            raise ValueError("hold_frames must be non-negative and analysis_width positive")
        self.min_motion_ratio = min_motion_ratio
        self.pixel_difference_threshold = pixel_difference_threshold
        self.hold_frames = hold_frames
        self.analysis_width = analysis_width
        self._previous: np.ndarray | None = None
        self._hold_remaining = 0

    def evaluate(self, frame: np.ndarray) -> MotionDecision:
        current = self._prepare(frame)
        if self._previous is None:
            self._previous = current
            return MotionDecision(False, 0.0, "CALIBRATING", 0)

        difference = np.abs(current.astype(np.int16) - self._previous.astype(np.int16))
        motion_ratio = float(np.mean(difference >= self.pixel_difference_threshold))
        self._previous = current

        if motion_ratio >= self.min_motion_ratio:
            self._hold_remaining = self.hold_frames
            return MotionDecision(True, motion_ratio, "MOTION", self._hold_remaining)
        if self._hold_remaining > 0:
            self._hold_remaining -= 1
            return MotionDecision(True, motion_ratio, "HOLD", self._hold_remaining)
        return MotionDecision(False, motion_ratio, "STILL", 0)

    def reset(self) -> None:
        self._previous = None
        self._hold_remaining = 0

    def _prepare(self, frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 3 and frame.shape[2] >= 3:
            # OpenCV supplies BGR. Integer weights keep this inexpensive.
            gray = (
                frame[..., 0].astype(np.uint16) * 29
                + frame[..., 1].astype(np.uint16) * 150
                + frame[..., 2].astype(np.uint16) * 77
            ) >> 8
            gray = gray.astype(np.uint8)
        elif frame.ndim == 2:
            gray = frame.astype(np.uint8, copy=False)
        else:
            raise ValueError("frame must be a grayscale or BGR image")

        height, width = gray.shape
        if width <= self.analysis_width:
            return gray.copy()
        target_height = max(1, round(height * self.analysis_width / width))
        ys = np.linspace(0, height - 1, target_height, dtype=np.intp)
        xs = np.linspace(0, width - 1, self.analysis_width, dtype=np.intp)
        return gray[np.ix_(ys, xs)]

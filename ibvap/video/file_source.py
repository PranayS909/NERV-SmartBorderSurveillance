import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import cv2

from video.base import VideoSource, NormalizedFrame

logger = logging.getLogger("ibvap.video.file")


class FileVideoSource(VideoSource):
    """Video source that reads from a local video file (MP4, AVI, etc.) with looping."""

    def __init__(self, camera_id: str, file_path: str, loop: bool = True, target_fps: float = 25.0):
        super().__init__(camera_id)
        self.file_path = str(file_path)
        self.loop = loop
        self.target_fps = target_fps
        self.frame_interval = 1.0 / max(1.0, target_fps)
        self.last_frame_time = 0.0
        self.cap: Optional[cv2.VideoCapture] = None
        self._open()

    def _open(self) -> bool:
        if not Path(self.file_path).exists():
            logger.warning("Video file not found at %s for camera %s", self.file_path, self.camera_id)
            return False
        self.cap = cv2.VideoCapture(self.file_path)
        if not self.cap.isOpened():
            logger.warning("Could not open video file %s for camera %s", self.file_path, self.camera_id)
            return False
        return True

    def is_open(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[NormalizedFrame]]:
        if not self.is_open():
            if self.loop:
                if not self._open():
                    return False, None
            else:
                return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            if self.loop:
                # Rewind video to start
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    return False, None
            else:
                return False, None

        self.frame_count += 1
        now_utc = datetime.now(timezone.utc)
        normalized = NormalizedFrame(
            camera_id=self.camera_id,
            frame_id=self.frame_count,
            timestamp=now_utc,
            frame=frame
        )
        return True, normalized

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

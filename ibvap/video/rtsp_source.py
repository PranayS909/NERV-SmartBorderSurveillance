import time
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import cv2

from video.base import VideoSource, NormalizedFrame

logger = logging.getLogger("ibvap.video.rtsp")


class RTSPVideoSource(VideoSource):
    """Video source for standard CCTV / NVR RTSP streaming feeds."""

    def __init__(self, camera_id: str, rtsp_url: str):
        super().__init__(camera_id)
        self.rtsp_url = rtsp_url.strip()
        self.cap: Optional[cv2.VideoCapture] = None
        self._connect()

    def _connect(self) -> bool:
        if not self.rtsp_url:
            return False
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            return self.cap.isOpened()
        except Exception:
            return False

    def is_open(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[NormalizedFrame]]:
        if not self.is_open():
            if not self._connect():
                return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.release()
            return False, None

        self.frame_count += 1
        return True, NormalizedFrame(
            camera_id=self.camera_id,
            frame_id=self.frame_count,
            timestamp=datetime.now(timezone.utc),
            frame=frame
        )

    def release(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

import time
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import cv2

from video.base import VideoSource, NormalizedFrame

logger = logging.getLogger("ibvap.video.phone")


class PhoneStreamSource(VideoSource):
    """
    Video source connecting to a live smartphone IP camera stream (e.g. IP Webcam app).
    Isolates live streaming logic and reconnects automatically without breaking the pipeline.
    """

    def __init__(self, camera_id: str, stream_url: str, reconnect_delay: float = 3.0):
        super().__init__(camera_id)
        self.stream_url = stream_url.strip()
        self.reconnect_delay = reconnect_delay
        self.last_reconnect_attempt = 0.0
        self.cap: Optional[cv2.VideoCapture] = None
        self._connect()

    def _connect(self) -> bool:
        if not self.stream_url:
            return False
        now = time.time()
        if now - self.last_reconnect_attempt < self.reconnect_delay:
            return False
        self.last_reconnect_attempt = now

        try:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.stream_url)
            if self.cap.isOpened():
                logger.info("Successfully connected live smartphone stream for %s at %s", self.camera_id, self.stream_url)
                return True
            else:
                logger.warning("Could not connect live smartphone stream for %s at %s", self.camera_id, self.stream_url)
                return False
        except Exception as exc:
            logger.warning("Exception opening smartphone stream for %s: %s", self.camera_id, exc)
            return False

    def is_open(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self) -> Tuple[bool, Optional[NormalizedFrame]]:
        if not self.is_open():
            if not self._connect():
                return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None or frame.size == 0:
            logger.warning("Lost frame from smartphone stream for camera %s. Attempting reconnection...", self.camera_id)
            self.release()
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
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

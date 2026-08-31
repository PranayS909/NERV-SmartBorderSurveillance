import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from video.base import VideoSource, NormalizedFrame
from video.file_source import FileVideoSource
from video.phone_source import PhoneStreamSource
from video.synthetic_source import SyntheticVideoSource

logger = logging.getLogger("ibvap.video.manager")


class VideoSourceManager:
    """
    Manages active VideoSource instances for all cameras.
    Supports seamless runtime mode switching between SAMPLE FOOTAGE and LIVE SMARTPHONE.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "demo/demo_config.json"
        self.mode = "SAMPLE"  # "SAMPLE" or "LIVE_PHONE"
        self.sources: Dict[str, VideoSource] = {}
        self.camera_configs = self._load_default_configs()
        self.initialize_sources()

    def _load_default_configs(self) -> dict:
        path = Path(self.config_path)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read %s: %s", path, e)

        # Baseline default fallback mapping
        return {
            "CAM-001": {
                "name": "BOP Main Gate",
                "sample_video": "demo/videos/intrusion.mp4",
                "sample_scenario": "intrusion",
                "phone_stream_url": "http://192.168.1.3:4747/video"
            },
            "CAM-002": {
                "name": "Checkpost Alpha",
                "sample_video": "demo/videos/vehicle_anpr.mp4",
                "sample_scenario": "anpr",
                "phone_stream_url": "http://192.168.1.4:4747/video"
            },
            "CAM-003": {
                "name": "Perimeter Fence North",
                "sample_video": "demo/videos/suspicious_object.mp4",
                "sample_scenario": "suspicious_object",
                "phone_stream_url": ""
            },
            "CAM-004": {
                "name": "Night Surveillance Post",
                "sample_video": "demo/videos/night.mp4",
                "sample_scenario": "night",
                "phone_stream_url": ""
            },
            "CAM-005": {
                "name": "Secondary Transit Gate",
                "sample_video": "demo/videos/cross_camera.mp4",
                "sample_scenario": "cross_camera",
                "phone_stream_url": ""
            }
        }

    def initialize_sources(self) -> None:
        """Create appropriate VideoSource instance for each configured camera."""
        # Release existing sources
        for src in self.sources.values():
            src.release()
        self.sources.clear()

        for cam_id, cfg in self.camera_configs.items():
            if self.mode == "LIVE_PHONE" and cfg.get("phone_stream_url"):
                # Use live phone stream
                source = PhoneStreamSource(cam_id, cfg["phone_stream_url"])
                # If cannot open stream immediately, fallback gracefully to file/synthetic
                if not source.is_open():
                    sample_file = cfg.get("sample_video", "")
                    if Path(sample_file).exists():
                        source = FileVideoSource(cam_id, sample_file)
                    else:
                        source = SyntheticVideoSource(cam_id, scenario=cfg.get("sample_scenario", "intrusion"))
                self.sources[cam_id] = source
            else:
                # Use sample footage (file or synthetic)
                sample_file = cfg.get("sample_video", "")
                if Path(sample_file).exists():
                    self.sources[cam_id] = FileVideoSource(cam_id, sample_file)
                else:
                    self.sources[cam_id] = SyntheticVideoSource(cam_id, scenario=cfg.get("sample_scenario", "intrusion"))

    def set_mode(self, mode: str) -> None:
        """Switch video source mode ('SAMPLE' or 'LIVE_PHONE')."""
        clean_mode = mode.upper()
        if clean_mode not in ("SAMPLE", "LIVE_PHONE"):
            raise ValueError(f"Unsupported mode: {mode}")
        if self.mode != clean_mode:
            logger.info("Switching video source mode to %s", clean_mode)
            self.mode = clean_mode
            self.initialize_sources()

    def get_source(self, camera_id: str) -> Optional[VideoSource]:
        return self.sources.get(camera_id)

    def read_frame(self, camera_id: str) -> Tuple[bool, Optional[NormalizedFrame]]:
        source = self.get_source(camera_id)
        if source is None:
            return False, None
        return source.read()

    def release_all(self) -> None:
        for src in self.sources.values():
            src.release()
        self.sources.clear()


# Global singleton instance
video_manager = VideoSourceManager()

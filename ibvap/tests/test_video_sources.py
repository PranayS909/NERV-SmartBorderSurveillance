import pytest
import numpy as np
from video.base import NormalizedFrame
from video.synthetic_source import SyntheticVideoSource
from video.phone_source import PhoneStreamSource
from video.manager import VideoSourceManager


def test_synthetic_source_normalized_frames():
    scenarios = ["intrusion", "vehicle", "anpr", "suspicious_object", "night", "cross_camera"]
    for sc in scenarios:
        src = SyntheticVideoSource(camera_id="CAM-001", scenario=sc)
        assert src.is_open() is True
        ok, nframe = src.read()
        assert ok is True
        assert isinstance(nframe, NormalizedFrame)
        assert nframe.camera_id == "CAM-001"
        assert nframe.frame_id == 1
        assert isinstance(nframe.frame, np.ndarray)
        assert nframe.shape == (480, 640, 3)
        src.release()


def test_phone_source_graceful_handling():
    # Attempt connecting to a non-existent URL; must not crash
    src = PhoneStreamSource(camera_id="CAM-PHONE", stream_url="http://127.0.0.1:9999/video")
    ok, nframe = src.read()
    assert ok is False
    assert nframe is None
    src.release()


def test_video_source_manager_mode_switching():
    mgr = VideoSourceManager()
    assert mgr.mode == "SAMPLE"
    assert "CAM-001" in mgr.sources

    ok, frame = mgr.read_frame("CAM-001")
    assert ok is True
    assert frame.camera_id == "CAM-001"

    # Switch to LIVE_PHONE
    mgr.set_mode("LIVE_PHONE")
    assert mgr.mode == "LIVE_PHONE"

    # Must still produce valid frames via fallback
    ok, frame = mgr.read_frame("CAM-001")
    assert ok is True

    # Switch back to SAMPLE
    mgr.set_mode("SAMPLE")
    assert mgr.mode == "SAMPLE"
    mgr.release_all()

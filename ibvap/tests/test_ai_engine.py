import pytest
import numpy as np
from ai.engine import (
    process_frame,
    _point_in_polygon,
    _check_zone_intrusion,
    _bbox_overlap,
    _is_night_frame,
    EngineManager,
)
from video.synthetic_source import SyntheticVideoSource


def test_point_in_polygon():
    poly = [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]]
    assert _point_in_polygon((50.0, 50.0), poly) is True
    assert _point_in_polygon((150.0, 50.0), poly) is False


def test_check_zone_intrusion():
    zones = [
        {
            "zone_id": "ZONE-TEST",
            "polygon": [[10.0, 10.0], [200.0, 10.0], [200.0, 200.0], [10.0, 200.0]],
        }
    ]
    # Centroid inside
    bbox_inside = [50.0, 50.0, 90.0, 90.0]
    assert _check_zone_intrusion(bbox_inside, zones) == "ZONE-TEST"

    # Centroid outside
    bbox_outside = [300.0, 300.0, 350.0, 350.0]
    assert _check_zone_intrusion(bbox_outside, zones) is None


def test_bbox_overlap():
    boxA = [10.0, 10.0, 50.0, 50.0]
    boxB = [40.0, 40.0, 80.0, 80.0]
    boxC = [100.0, 100.0, 150.0, 150.0]
    assert _bbox_overlap(boxA, boxB) is True
    assert _bbox_overlap(boxA, boxC) is False


def test_is_night_frame():
    dark_frame = np.full((100, 100, 3), 30, dtype=np.uint8)
    bright_frame = np.full((100, 100, 3), 150, dtype=np.uint8)
    assert _is_night_frame(dark_frame) is True
    assert _is_night_frame(bright_frame) is False


def test_process_frame():
    src = SyntheticVideoSource("CAM-001", scenario="intrusion")
    ok, norm = src.read()
    assert ok is True
    assert norm is not None

    annotated, events = process_frame("CAM-001", norm.frame, norm.frame_id)
    assert annotated is not None
    assert annotated.shape == norm.frame.shape
    assert isinstance(events, list)


def test_engine_manager_lifecycle():
    mgr = EngineManager()
    mgr.start(["CAM-001"])
    assert "CAM-001" in mgr.running_cameras()
    mgr.stop(["CAM-001"])
    assert "CAM-001" not in mgr.running_cameras()


import numpy as np
import pytest

from ai.motion_gate import MotionGate


def test_motion_gate_sleeps_then_wakes_and_holds():
    gate = MotionGate(min_motion_ratio=0.05, pixel_difference_threshold=20, hold_frames=2, analysis_width=40)
    still = np.zeros((40, 80, 3), dtype=np.uint8)
    moved = still.copy()
    moved[:, :20] = 255

    assert gate.evaluate(still).reason == "CALIBRATING"
    assert gate.evaluate(still).awake is False
    motion = gate.evaluate(moved)
    assert motion.awake is True and motion.reason == "MOTION"
    assert gate.evaluate(moved).reason == "HOLD"
    assert gate.evaluate(moved).reason == "HOLD"
    assert gate.evaluate(moved).awake is False


def test_motion_gate_validates_configuration_and_frame_shape():
    with pytest.raises(ValueError):
        MotionGate(min_motion_ratio=1.1)
    gate = MotionGate()
    with pytest.raises(ValueError):
        gate.evaluate(np.zeros((10,), dtype=np.uint8))

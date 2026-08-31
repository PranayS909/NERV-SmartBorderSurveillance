"""
demo/generate_clips.py — Generate synthetic demo MP4 video clips for IBVAP.

Generates 30-second 640×480 @25fps clips for:
  - intrusion.mp4
  - vehicle_anpr.mp4
  - suspicious_object.mp4
  - night.mp4
  - cross_camera.mp4

Usage:
    python demo/generate_clips.py
"""

import sys
import math
import time
from pathlib import Path

# Must run from ibvap/ root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from datetime import datetime, timezone

VIDEOS_DIR = ROOT / "demo" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 640, 480
FPS = 25
DURATION_SEC = 30
TOTAL_FRAMES = FPS * DURATION_SEC

FOURCC = cv2.VideoWriter_fourcc(*"mp4v")


def put_hud(frame, camera_id, scenario, frame_idx):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cv2.putText(frame, f"IBVAP | {camera_id} [{scenario}]", (15, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (52, 217, 180), 2, cv2.LINE_AA)
    cv2.putText(frame, ts, (15, HEIGHT - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 155, 170), 1)
    cv2.putText(frame, f"FRM {frame_idx:05d}", (WIDTH - 130, HEIGHT - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 110, 120), 1)


def draw_outpost_bg(frame):
    """Standard daylight outpost background."""
    frame[:] = (48, 56, 64)
    # Asphalt road
    road_pts = np.array([[190, HEIGHT], [450, HEIGHT], [370, 180], [270, 180]], dtype=np.int32)
    cv2.fillPoly(frame, [road_pts], (60, 68, 76))
    # Border fence
    cv2.line(frame, (0, 190), (WIDTH, 190), (85, 95, 108), 2)
    for fx in range(0, WIDTH, 28):
        cv2.line(frame, (fx, 175), (fx, 191), (85, 95, 108), 1)
    # Zone box
    cv2.rectangle(frame, (115, 95), (595, 405), (0, 120, 255), 1)
    cv2.putText(frame, "ZONE-01 RESTRICTED", (125, 118),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 120, 255), 1)


def draw_night_bg(frame):
    frame[:] = (10, 14, 18)
    for y in range(0, HEIGHT, 38):
        cv2.line(frame, (0, y), (WIDTH, y), (16, 22, 28), 1)
    for x in range(0, WIDTH, 38):
        cv2.line(frame, (x, 0), (x, HEIGHT), (16, 22, 28), 1)


# ─── Scenario generators ─────────────────────────────────────────────────────

def gen_intrusion(out_path: Path):
    writer = cv2.VideoWriter(str(out_path), FOURCC, FPS, (WIDTH, HEIGHT))
    for fi in range(TOTAL_FRAMES):
        t = fi * 0.04
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_outpost_bg(frame)
        px = int(130 + (fi * 3.2) % (WIDTH - 220))
        py = int(210 + 35 * math.sin(t))
        # Person silhouette
        cv2.circle(frame, (px + 18, py + 14), 13, (185, 195, 205), -1)
        cv2.rectangle(frame, (px + 4, py + 28), (px + 34, py + 90), (145, 155, 165), -1)
        # Track bounding box
        cv2.rectangle(frame, (px - 2, py - 2), (px + 42, py + 98), (52, 217, 180), 2)
        cv2.putText(frame, "PERSON #31 0.91", (px - 5, py - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (52, 217, 180), 1)
        # Intrusion alert banner
        if 60 < fi < TOTAL_FRAMES - 30:
            cv2.rectangle(frame, (0, 0), (460, 32), (10, 10, 50), -1)
            cv2.putText(frame, "  ⚡ INTRUSION [HIGH] — ZONE-01", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (52, 217, 180), 1)
        put_hud(frame, "CAM-001", "INTRUSION", fi)
        writer.write(frame)
    writer.release()
    print(f"[OK] {out_path.name}")


def gen_vehicle_anpr(out_path: Path):
    writer = cv2.VideoWriter(str(out_path), FOURCC, FPS, (WIDTH, HEIGHT))
    plates = ["MH12AB1234", "DL01CA9988", "GJ05ZZ5050"]
    plate_idx = 0
    for fi in range(TOTAL_FRAMES):
        t = fi * 0.035
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_outpost_bg(frame)
        vx = int(225 + 18 * math.sin(t * 0.4))
        vy = int(155 + (fi * 2.5) % 240)
        vw, vh = 165, 88
        # Vehicle body
        cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), (180, 120, 40), -1)
        cv2.rectangle(frame, (vx + 18, vy + 10), (vx + vw - 18, vy + 40), (220, 230, 240), -1)
        # Number plate
        plate = plates[plate_idx % len(plates)]
        cv2.rectangle(frame, (vx + 38, vy + vh - 22), (vx + vw - 36, vy + vh - 5), (255, 255, 255), -1)
        cv2.putText(frame, plate, (vx + 42, vy + vh - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1)
        cv2.rectangle(frame, (vx - 3, vy - 3), (vx + vw + 3, vy + vh + 3), (255, 150, 40), 2)
        cv2.putText(frame, f"CAR #{17 + plate_idx} 0.93", (vx, vy - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 150, 40), 1)
        # ANPR banner
        if fi % 90 < 60:
            cv2.rectangle(frame, (0, 0), (WIDTH, 32), (10, 10, 50), -1)
            cv2.putText(frame, f"  ANPR: {plate} — VEHICLE DETECTED [LOW]", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (52, 217, 180), 1)
        if fi % 90 == 0:
            plate_idx += 1
        put_hud(frame, "CAM-002", "ANPR", fi)
        writer.write(frame)
    writer.release()
    print(f"[OK] {out_path.name}")


def gen_suspicious_object(out_path: Path):
    writer = cv2.VideoWriter(str(out_path), FOURCC, FPS, (WIDTH, HEIGHT))
    for fi in range(TOTAL_FRAMES):
        t = fi * 0.038
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_outpost_bg(frame)
        px = int(245 + 28 * math.sin(t * 0.7))
        py = 195
        # Person
        cv2.circle(frame, (px + 16, py + 14), 13, (185, 195, 205), -1)
        cv2.rectangle(frame, (px + 3, py + 28), (px + 32, py + 92), (130, 140, 150), -1)
        # Weapon
        cv2.rectangle(frame, (px + 30, py + 42), (px + 72, py + 54), (0, 0, 200), -1)
        # Alert bboxes
        cv2.rectangle(frame, (px - 5, py - 5), (px + 80, py + 100), (0, 0, 255), 2)
        cv2.putText(frame, "WEAPON DETECTED 0.87", (px - 5, py - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 60, 255), 1)
        # Alert banner
        if fi > 30:
            cv2.rectangle(frame, (0, 0), (WIDTH, 32), (10, 10, 50), -1)
            cv2.putText(frame, "  ⚡ SUSPICIOUS OBJECT [CRITICAL] — ARMED PERSON", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 80, 255), 1)
        put_hud(frame, "CAM-003", "SUSPICIOUS_OBJECT", fi)
        writer.write(frame)
    writer.release()
    print(f"[OK] {out_path.name}")


def gen_night(out_path: Path):
    writer = cv2.VideoWriter(str(out_path), FOURCC, FPS, (WIDTH, HEIGHT))
    for fi in range(TOTAL_FRAMES):
        t = fi * 0.042
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_night_bg(frame)
        px = int(80 + (fi * 2.1) % (WIDTH - 180))
        py = int(190 + 28 * math.sin(t))
        # IR heat blob
        for r, alpha in [(32, 60), (20, 120), (10, 200)]:
            overlay = frame.copy()
            cv2.ellipse(overlay, (px + 22, py + 45), (r, r + 18), 0, 0, 360,
                        (30, 160, 200), -1)
            cv2.addWeighted(overlay, alpha / 255.0, frame, 1 - alpha / 255.0, 0, frame)
        cv2.rectangle(frame, (px - 4, py - 4), (px + 50, py + 106), (40, 220, 240), 2)
        cv2.putText(frame, "IR MOVEMENT 0.78", (px - 4, py - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 220, 240), 1)
        if fi > 40:
            cv2.rectangle(frame, (0, 0), (WIDTH, 32), (10, 10, 50), -1)
            cv2.putText(frame, "  ⚡ NIGHT MOVEMENT [HIGH] — THERMAL SIGNATURE", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 220, 240), 1)
        put_hud(frame, "CAM-004", "NIGHT", fi)
        writer.write(frame)
    writer.release()
    print(f"[OK] {out_path.name}")


def gen_cross_camera(out_path: Path):
    writer = cv2.VideoWriter(str(out_path), FOURCC, FPS, (WIDTH, HEIGHT))
    for fi in range(TOTAL_FRAMES):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_outpost_bg(frame)
        # Vehicle parked
        cv2.rectangle(frame, (310, 205), (468, 302), (180, 120, 40), -1)
        cv2.rectangle(frame, (325, 218), (455, 252), (220, 230, 240), -1)
        cv2.rectangle(frame, (307, 202), (471, 305), (255, 150, 40), 2)
        cv2.putText(frame, "VEHICLE #17 0.90", (310, 196),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 150, 40), 1)
        # Person approaching vehicle
        progress = fi % 150
        if progress < 75:
            px = int(145 + progress * 2.3)
            py = 228
        else:
            px = int(318 - (progress - 75) * 2.0)
            py = 228
        cv2.circle(frame, (px + 14, py + 12), 11, (185, 195, 205), -1)
        cv2.rectangle(frame, (px + 2, py + 24), (px + 28, py + 82), (145, 155, 165), -1)
        cv2.rectangle(frame, (px - 2, py - 2), (px + 34, py + 90), (52, 217, 180), 2)
        cv2.putText(frame, "PERSON #31 0.91", (px - 2, py - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (52, 217, 180), 1)
        # Association event when overlap
        if abs(px - 310) < 60:
            cv2.rectangle(frame, (0, 0), (WIDTH, 32), (10, 10, 50), -1)
            cv2.putText(frame, "  PERSON-VEHICLE ASSOC [MEDIUM] — PERSON #31 → VEH #17", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (52, 217, 180), 1)
        put_hud(frame, "CAM-005", "CROSS_CAMERA", fi)
        writer.write(frame)
    writer.release()
    print(f"[OK] {out_path.name}")


if __name__ == "__main__":
    print(f"Generating demo clips in {VIDEOS_DIR}...")
    gen_intrusion(VIDEOS_DIR / "intrusion.mp4")
    gen_vehicle_anpr(VIDEOS_DIR / "vehicle_anpr.mp4")
    gen_suspicious_object(VIDEOS_DIR / "suspicious_object.mp4")
    gen_night(VIDEOS_DIR / "night.mp4")
    gen_cross_camera(VIDEOS_DIR / "cross_camera.mp4")
    print("\nAll demo clips generated successfully.")

import time
import math
from datetime import datetime, timezone
from typing import Optional, Tuple
import numpy as np
import cv2

from video.base import VideoSource, NormalizedFrame


class SyntheticVideoSource(VideoSource):
    """
    Generates synthetic CCTV video frames with simulated moving objects.
    Guarantees 100% deterministic demo execution even when offline without video files.
    """

    def __init__(self, camera_id: str, scenario: str = "intrusion", width: int = 640, height: int = 480):
        super().__init__(camera_id)
        self.scenario = scenario
        self.width = width
        self.height = height
        self.running = True

    def is_open(self) -> bool:
        return self.running

    def read(self) -> Tuple[bool, Optional[NormalizedFrame]]:
        if not self.running:
            return False, None

        self.frame_count += 1
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Base background colors depending on night or day
        if self.scenario == "night":
            frame[:] = (12, 16, 20)  # Dark night palette
        else:
            frame[:] = (45, 52, 58)  # Outpost ground palette

        # Draw outpost background infrastructure (road, fence, gate)
        if self.scenario != "night":
            # Road / tarmac
            cv2.fillPoly(frame, [np.array([[180, 480], [460, 480], [380, 200], [260, 200]])], (60, 68, 75))
            # Border fence line
            cv2.line(frame, (0, 200), (640, 200), (90, 100, 110), 2)
            for fx in range(0, 640, 30):
                cv2.line(frame, (fx, 180), (fx, 200), (90, 100, 110), 1)

            # Restricted Zone polygon visualization
            zone_pts = np.array([[120, 100], [600, 100], [600, 400], [120, 400]], dtype=np.int32)
            cv2.polylines(frame, [zone_pts], True, (0, 120, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "ZONE-01 (RESTRICTED)", (130, 125),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 255), 1)
        else:
            # Night Infrared Grid
            for y in range(0, self.height, 40):
                cv2.line(frame, (0, y), (self.width, y), (18, 24, 30), 1)
            for x in range(0, self.width, 40):
                cv2.line(frame, (x, 0), (x, self.height), (18, 24, 30), 1)

        t = self.frame_count * 0.04
        
        # Render synthetic scenario objects
        if self.scenario == "intrusion":
            # Person moving into the restricted zone
            px = int(100 + (self.frame_count * 3) % (self.width - 200))
            py = int(220 + 40 * math.sin(t))
            # Draw synthetic person silhouette
            cv2.circle(frame, (px + 15, py + 15), 12, (180, 190, 200), -1)  # Head
            cv2.rectangle(frame, (px, py + 30), (px + 30, py + 95), (140, 150, 160), -1)  # Torso/legs
            cv2.putText(frame, "PERSON #31", (px - 10, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 210, 220), 1)

        elif self.scenario in ("vehicle", "anpr"):
            # Vehicle driving down the outpost road
            vx = int(220 + 20 * math.sin(t * 0.5))
            vy = int(180 + (self.frame_count * 2.5) % 240)
            vw, vh = 160, 90
            cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), (180, 120, 40), -1)
            # Windshield & Roof
            cv2.rectangle(frame, (vx + 20, vy + 10), (vx + vw - 20, vy + 40), (220, 220, 220), -1)
            # Number plate MH12AB1234
            cv2.rectangle(frame, (vx + 35, vy + vh - 22), (vx + vw - 35, vy + vh - 5), (255, 255, 255), -1)
            cv2.putText(frame, "MH12AB1234", (vx + 40, vy + vh - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

        elif self.scenario == "suspicious_object":
            # Person with an armed object
            px = int(280 + 30 * math.sin(t * 0.8))
            py = 220
            cv2.circle(frame, (px + 15, py + 15), 12, (180, 190, 200), -1)
            cv2.rectangle(frame, (px, py + 30), (px + 30, py + 95), (120, 130, 140), -1)
            # Weapon-like object
            cv2.rectangle(frame, (px + 28, py + 45), (px + 60, py + 55), (0, 0, 180), -1)
            cv2.putText(frame, "SUSPICIOUS ITEM", (px + 28, py + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        elif self.scenario == "night":
            # Thermal / low-light silhouette moving
            px = int(80 + (self.frame_count * 2) % (self.width - 160))
            py = int(200 + 30 * math.sin(t))
            # Low light heat blob
            cv2.ellipse(frame, (px + 20, py + 40), (25, 45), 0, 0, 360, (40, 180, 220), -1)
            cv2.putText(frame, "IR MOVEMENT", (px - 5, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 220, 240), 1)

        elif self.scenario == "cross_camera":
            # Person approaching vehicle
            progress = (self.frame_count % 150)
            if progress < 75:
                # Person moving towards vehicle
                px = int(140 + progress * 2)
                py = 240
                cv2.circle(frame, (px + 10, py + 10), 10, (180, 190, 200), -1)
                cv2.rectangle(frame, (px, py + 22), (px + 20, py + 70), (140, 150, 160), -1)
                cv2.putText(frame, "PERSON #31", (px - 10, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 210, 220), 1)
            # Vehicle waiting
            cv2.rectangle(frame, (320, 220), (460, 300), (180, 120, 40), -1)
            cv2.putText(frame, "VEHICLE #17", (330, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 180, 50), 1)

        # Draw HUD Timestamp and Camera ID
        ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
        cv2.putText(frame, f"CAM: {self.camera_id} [{self.scenario.upper()}]", (15, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (52, 217, 180), 2)
        cv2.putText(frame, ts_str, (15, self.height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 175, 190), 1)

        now_utc = datetime.now(timezone.utc)
        return True, NormalizedFrame(
            camera_id=self.camera_id,
            frame_id=self.frame_count,
            timestamp=now_utc,
            frame=frame
        )

    def release(self) -> None:
        self.running = False

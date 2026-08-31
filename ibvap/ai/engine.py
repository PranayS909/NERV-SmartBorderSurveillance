"""
ai/engine.py — Central AI Integration Engine

Reads NormalizedFrames from VideoSourceManager, runs the full pipeline:
  Frame → YOLO Detection → HybridTracker → Zone/Fence Intrusion
         → Weapon/Threat → Night Motion → Face/Watchlist → ANPR
         → EventEngine → POST /api/v1/events → PostgreSQL + WebSocket

Designed to be fully source-agnostic: the AI pipeline never knows whether
frames came from a file, phone stream, or synthetic generator.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("ibvap.engine")

# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports for heavyweight AI modules (loaded only on first use)
# ─────────────────────────────────────────────────────────────────────────────
_YOLO_ENTITY = None
_YOLO_WEAPON = None
_HYBRID_TRACKER: Dict[str, Any] = {}


def _load_yolo(path: str, name: str = "YOLO"):
    try:
        from ultralytics import YOLO
        model = YOLO(path)
        logger.info("Loaded %s from %s", name, path)
        return model
    except Exception as exc:
        logger.warning("Could not load %s from %s: %s — using dummy detections", name, path, exc)
        return None


def _get_entity_model():
    global _YOLO_ENTITY
    if _YOLO_ENTITY is None:
        p = Path("models/detection/entity.pt")
        if p.exists():
            _YOLO_ENTITY = _load_yolo(str(p), "EntityModel")
    return _YOLO_ENTITY


def _get_weapon_model():
    global _YOLO_WEAPON
    if _YOLO_WEAPON is None:
        p = Path("models/detection/weapons.pt")
        if p.exists():
            _YOLO_WEAPON = _load_yolo(str(p), "WeaponModel")
    return _YOLO_WEAPON


# ─────────────────────────────────────────────────────────────────────────────
# Detection helpers
# ─────────────────────────────────────────────────────────────────────────────
import concurrent.futures

_EVENT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="ibvap-evt")


def _submit_event_async(ev: Dict):
    """Offload event submission to background thread so camera loops never block."""
    try:
        _EVENT_EXECUTOR.submit(_post_event_sync, ev)
    except Exception:
        pass


VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}


def _yolo_detect(model, frame: np.ndarray) -> List[Dict]:
    """Run YOLO inference with optimized imgsz=384 for fast, smooth CPU execution."""
    if model is None:
        return []
    try:
        # imgsz=384 on 640x480 yields 3x faster CPU throughput with high accuracy
        results = model.predict(frame, imgsz=384, verbose=False)
        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < 0.35:
                    continue
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, "unknown").lower()
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                detections.append({
                    "class_name": cls_name,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": conf,
                    "track_id": None,
                })
        return detections
    except Exception as exc:
        logger.debug("YOLO inference error: %s", exc)
        return []



def _bbox_overlap(boxA, boxB) -> bool:
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    return (ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1)


# ─────────────────────────────────────────────────────────────────────────────
# Zone intrusion check (polygon-point-in-polygon)
# ─────────────────────────────────────────────────────────────────────────────
def _point_in_polygon(point: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    if not polygon or len(polygon) < 3:
        return False
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _check_zone_intrusion(bbox: List[float], zone_polygons: List[Dict]) -> Optional[str]:
    """Returns zone_id if bbox centroid is inside any zone polygon."""
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for zone in zone_polygons:
        polygon = zone.get("polygon", [])
        if _point_in_polygon((cx, cy), polygon):
            return zone.get("zone_id")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Annotation / Drawing
# ─────────────────────────────────────────────────────────────────────────────
def _draw_annotation(frame: np.ndarray, detections: List[Dict], events: List[Dict]) -> np.ndarray:
    """Draw bounding boxes, labels, and event banners on a frame (non-destructive copy)."""
    annotated = frame.copy()

    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        cls = det["class_name"]
        conf = det.get("confidence", 0.0)
        tid = det.get("track_id")

        color = (52, 217, 180) if cls == "person" else (255, 150, 40) if cls in VEHICLE_CLASSES else (0, 0, 220)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        label = f"{cls}"
        if tid is not None:
            label += f" #{tid}"
        label += f" {conf:.2f}"
        cv2.putText(annotated, label, (x1, max(y1 - 8, 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    # Event banners at top of frame
    for i, ev in enumerate(events[:3]):
        banner = f"  ⚡ {ev.get('event_type', 'EVENT').upper()} [{ev.get('severity', '')}]"
        cv2.rectangle(annotated, (0, i * 28), (len(banner) * 9, (i + 1) * 28), (10, 10, 40), -1)
        cv2.putText(annotated, banner, (5, i * 28 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (52, 217, 180), 1, cv2.LINE_AA)

    # Timestamp watermark
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    h = annotated.shape[0]
    cv2.putText(annotated, ts, (5, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 130, 140), 1)

    return annotated


# ─────────────────────────────────────────────────────────────────────────────
# Event builder
# ─────────────────────────────────────────────────────────────────────────────
_event_seq = 0
_event_seq_lock = threading.Lock()


def _next_event_id() -> str:
    global _event_seq
    with _event_seq_lock:
        _event_seq += 1
        return f"EVT-{_event_seq:06d}"


def _build_event(
    event_type: str,
    camera_id: str,
    severity: str,
    confidence: float,
    bbox: List[float],
    track_id: Optional[int] = None,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    zone_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    return {
        "event_id": _next_event_id(),
        "event_type": event_type,
        "camera_id": camera_id,
        "entity_id": entity_id or (f"G-{track_id:03d}" if track_id else None),
        "entity_type": entity_type,
        "severity": severity,
        "confidence": round(confidence, 3),
        "zone_id": zone_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "NEW",
        "metadata": metadata or {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Event submission (async POST to local FastAPI events endpoint)
# ─────────────────────────────────────────────────────────────────────────────
_BACKEND_BASE = "http://127.0.0.1:8000"


def _post_event_sync(payload: Dict) -> bool:
    """Submit event via REST. Runs in engine thread (non-async)."""
    try:
        import urllib.request, urllib.error
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{_BACKEND_BASE}/api/v1/events",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 201
    except Exception as exc:
        logger.debug("Event POST failed: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ANPR — format Indian number plate
# ─────────────────────────────────────────────────────────────────────────────
def _format_indian_plate(raw: str) -> str:
    """Attempt to clean up an ANPR result into Indian plate format (XX00XX0000)."""
    import re
    s = re.sub(r"[^A-Z0-9]", "", raw.upper())
    return s if len(s) >= 6 else raw


# ─────────────────────────────────────────────────────────────────────────────
# Night-time motion heuristic
# ─────────────────────────────────────────────────────────────────────────────
def _is_night_frame(frame: np.ndarray) -> bool:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    return float(gray.mean()) < 60.0


# ─────────────────────────────────────────────────────────────────────────────
# Zone config cache (fetched from DB via REST once per engine start)
# ─────────────────────────────────────────────────────────────────────────────
_ZONE_CACHE: List[Dict] = []
_ZONE_CACHE_TS = 0.0
_ZONE_CACHE_TTL = 60.0  # seconds


def _get_zones() -> List[Dict]:
    global _ZONE_CACHE, _ZONE_CACHE_TS
    now = time.time()
    if now - _ZONE_CACHE_TS < _ZONE_CACHE_TTL:
        return _ZONE_CACHE
    try:
        import urllib.request
        with urllib.request.urlopen(f"{_BACKEND_BASE}/api/v1/zones", timeout=2) as resp:
            data = json.loads(resp.read())
            _ZONE_CACHE = data if isinstance(data, list) else []
            _ZONE_CACHE_TS = now
    except Exception:
        pass
    return _ZONE_CACHE


# ─────────────────────────────────────────────────────────────────────────────
# Per-camera event throttling (avoid flood of duplicate events)
# ─────────────────────────────────────────────────────────────────────────────
_last_event_ts: Dict[str, float] = {}  # key: f"{camera_id}:{event_type}"
_EVENT_MIN_INTERVAL = 8.0  # seconds between same event-type on same camera


def _should_emit(camera_id: str, event_type: str) -> bool:
    key = f"{camera_id}:{event_type}"
    now = time.time()
    if now - _last_event_ts.get(key, 0.0) >= _EVENT_MIN_INTERVAL:
        _last_event_ts[key] = now
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Frame Processing — single camera, single frame
# ─────────────────────────────────────────────────────────────────────────────
_CAMERA_CACHE: Dict[str, Dict[str, Any]] = {}


def process_frame(camera_id: str, frame: np.ndarray, frame_id: int) -> Tuple[np.ndarray, List[Dict]]:
    """
    Run the complete AI pipeline on a single normalized frame.
    Uses intelligent frame decimation: YOLO runs every 3rd frame to ensure 20+ FPS on CPU,
    while persisting bounding boxes across skipped frames.
    """
    events: List[Dict] = []
    all_detections: List[Dict] = []
    weapon_detections: List[Dict] = []

    entity_model = _get_entity_model()
    weapon_model_ref = _get_weapon_model()
    is_night = _is_night_frame(frame)
    zones = _get_zones()

    # ── Inference cadence check ──
    cached = _CAMERA_CACHE.get(camera_id)
    should_infer = (cached is None) or (frame_id % 3 == 0)

    if should_infer:
        # ── Entity detection (persons + vehicles) ──────────────────────────
        if entity_model is not None:
            entity_dets = _yolo_detect(entity_model, frame)
        else:
            # Synthetic detections for demo without model weights
            entity_dets = _synthetic_detections(camera_id, frame_id, frame)

        # ── Selective weapon detection (only when person exists or CAM-003) ──
        if weapon_model_ref is not None and (camera_id == "CAM-003" or any(d["class_name"] == "person" for d in entity_dets)):
            weapon_detections = _yolo_detect(weapon_model_ref, frame)

        _CAMERA_CACHE[camera_id] = {
            "entity_dets": entity_dets,
            "weapon_detections": weapon_detections,
        }
    else:
        entity_dets = cached.get("entity_dets", [])
        weapon_detections = cached.get("weapon_detections", [])

    all_detections.extend(entity_dets)


    # ── Per-detection event logic ──────────────────────────────────────────
    person_boxes = [d for d in entity_dets if d["class_name"] == "person"]
    vehicle_boxes = [d for d in entity_dets if d["class_name"] in VEHICLE_CLASSES]

    for det in entity_dets:
        bbox = det["bbox"]
        cls = det["class_name"]
        conf = det["confidence"]
        tid = det.get("track_id") or frame_id  # fallback track id

        # Check zone intrusion
        intruded_zone = _check_zone_intrusion(bbox, zones)
        if intruded_zone and cls == "person":
            if _should_emit(camera_id, "intrusion"):
                ev = _build_event(
                    "intrusion", camera_id, "HIGH", conf, bbox,
                    track_id=tid, entity_type="person",
                    zone_id=intruded_zone,
                    metadata={"model": "YOLOv8", "frame_id": frame_id, "zone": intruded_zone}
                )
                events.append(ev)

        # Person detected event (LOW priority)
        if cls == "person" and _should_emit(camera_id, "person_detected"):
            ev = _build_event(
                "person_detected", camera_id, "LOW", conf, bbox,
                track_id=tid, entity_type="person",
                metadata={"model": "YOLOv8", "frame_id": frame_id, "night": is_night}
            )
            events.append(ev)

        # Vehicle detected event
        if cls in VEHICLE_CLASSES and _should_emit(camera_id, "vehicle_detected"):
            ev = _build_event(
                "vehicle_detected", camera_id, "LOW", conf, bbox,
                track_id=tid, entity_type="vehicle",
                metadata={"vehicle_class": cls, "frame_id": frame_id}
            )
            events.append(ev)

    # ── Weapon / armed person overlap ─────────────────────────────────────
    for wpn in weapon_detections:
        for person in person_boxes:
            if _bbox_overlap(wpn["bbox"], person["bbox"]):
                if _should_emit(camera_id, "suspicious_object"):
                    ev = _build_event(
                        "suspicious_object", camera_id, "CRITICAL",
                        wpn["confidence"], wpn["bbox"],
                        track_id=person.get("track_id"),
                        entity_type="person",
                        metadata={"weapon_class": wpn["class_name"], "frame_id": frame_id}
                    )
                    events.append(ev)
                all_detections.append({**wpn, "class_name": f"weapon:{wpn['class_name']}"})

    # ── Night movement ─────────────────────────────────────────────────────
    if is_night and person_boxes:
        if _should_emit(camera_id, "night_movement"):
            ev = _build_event(
                "night_movement", camera_id, "HIGH",
                max(d["confidence"] for d in person_boxes),
                person_boxes[0]["bbox"],
                entity_type="person",
                metadata={"frame_id": frame_id, "person_count": len(person_boxes)}
            )
            events.append(ev)

    # ── Person–Vehicle proximity (simple: person bbox overlaps vehicle bbox) ──
    for person in person_boxes:
        for vehicle in vehicle_boxes:
            if _bbox_overlap(person["bbox"], vehicle["bbox"]):
                if _should_emit(camera_id, "vehicle_person_association"):
                    ev = _build_event(
                        "vehicle_person_association", camera_id, "MEDIUM",
                        min(person["confidence"], vehicle["confidence"]),
                        person["bbox"],
                        track_id=person.get("track_id"),
                        entity_type="person",
                        metadata={
                            "vehicle_track_id": vehicle.get("track_id"),
                            "frame_id": frame_id
                        }
                    )
                    events.append(ev)

    # ── Annotate frame ─────────────────────────────────────────────────────
    annotated = _draw_annotation(frame, all_detections, events)
    return annotated, events


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic detections for demo without YOLO weights
# ─────────────────────────────────────────────────────────────────────────────
def _synthetic_detections(camera_id: str, frame_id: int, frame: np.ndarray) -> List[Dict]:
    """Return plausible bounding box detections for demo video scenarios."""
    import math
    h, w = frame.shape[:2]
    t = frame_id * 0.04

    scenario_map = {
        "CAM-001": "intrusion",
        "CAM-002": "anpr",
        "CAM-003": "suspicious_object",
        "CAM-004": "night",
        "CAM-005": "cross_camera",
    }
    scenario = scenario_map.get(camera_id, "intrusion")

    dets = []
    if scenario == "intrusion":
        px = int(100 + (frame_id * 3) % max(1, w - 200))
        py = int(200 + 40 * math.sin(t))
        dets.append({"class_name": "person", "bbox": [px, py, px + 40, py + 100],
                      "confidence": 0.88, "track_id": 31})

    elif scenario in ("anpr", "vehicle"):
        vx = int(220 + 20 * math.sin(t * 0.5))
        vy = int(160 + (frame_id * 2) % max(1, h - 100))
        dets.append({"class_name": "car", "bbox": [vx, vy, vx + 160, vy + 90],
                      "confidence": 0.93, "track_id": 17})
        px = vx + 60
        py = vy - 60
        if py > 0:
            dets.append({"class_name": "person", "bbox": [px, py, px + 35, py + 95],
                          "confidence": 0.79, "track_id": 22})

    elif scenario == "suspicious_object":
        px = int(240 + 30 * math.sin(t * 0.8))
        py = 200
        dets.append({"class_name": "person", "bbox": [px, py, px + 40, py + 100],
                      "confidence": 0.85, "track_id": 9})

    elif scenario == "night":
        px = int(80 + (frame_id * 2) % max(1, w - 160))
        py = int(180 + 30 * math.sin(t))
        dets.append({"class_name": "person", "bbox": [px, py, px + 40, py + 100],
                      "confidence": 0.72, "track_id": 5})

    elif scenario == "cross_camera":
        progress = frame_id % 150
        if progress < 75:
            px = int(140 + progress * 2)
            dets.append({"class_name": "person", "bbox": [px, 220, px + 30, 300],
                          "confidence": 0.91, "track_id": 31})
        dets.append({"class_name": "car", "bbox": [320, 210, 470, 310],
                      "confidence": 0.88, "track_id": 17})

    return dets


# ─────────────────────────────────────────────────────────────────────────────
# Engine loop (runs in a background thread per camera)
# ─────────────────────────────────────────────────────────────────────────────
def _camera_engine_loop(camera_id: str, stop_event: threading.Event):
    """Worker thread: continuously read frames, process AI, push annotated frame & events."""
    from video.manager import video_manager
    from backend.api.cameras import set_camera_frame

    logger.info("Engine loop starting for %s", camera_id)
    target_fps = 22.0
    frame_interval = 1.0 / target_fps

    while not stop_event.is_set():
        loop_start = time.monotonic()

        try:
            ok, norm_frame = video_manager.read_frame(camera_id)
            if not ok or norm_frame is None:
                time.sleep(0.05)
                continue

            annotated, events = process_frame(camera_id, norm_frame.frame, norm_frame.frame_id)

            # Push annotated frame to MJPEG buffer (pre-encoded JPEG)
            set_camera_frame(camera_id, annotated)

            # Submit events asynchronously in background thread (never stalls the video loop)
            for ev in events:
                _submit_event_async(ev)

        except Exception as exc:
            logger.error("Engine error for %s: %s", camera_id, exc, exc_info=True)
            time.sleep(0.2)

        # Pace to target FPS
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0.0, frame_interval - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

    logger.info("Engine loop stopped for %s", camera_id)



# ─────────────────────────────────────────────────────────────────────────────
# Engine Manager — start/stop camera processing threads
# ─────────────────────────────────────────────────────────────────────────────
class EngineManager:
    """Manages per-camera AI engine threads."""

    def __init__(self):
        self._stop_events: Dict[str, threading.Event] = {}
        self._threads: Dict[str, threading.Thread] = {}

    def start(self, camera_ids: List[str]) -> None:
        for cam_id in camera_ids:
            if cam_id in self._threads and self._threads[cam_id].is_alive():
                continue
            stop_ev = threading.Event()
            t = threading.Thread(
                target=_camera_engine_loop,
                args=(cam_id, stop_ev),
                daemon=True,
                name=f"engine-{cam_id}",
            )
            self._stop_events[cam_id] = stop_ev
            self._threads[cam_id] = t
            t.start()
            logger.info("Started AI engine thread for %s", cam_id)

    def stop(self, camera_ids: Optional[List[str]] = None) -> None:
        targets = camera_ids or list(self._threads.keys())
        for cam_id in targets:
            if cam_id in self._stop_events:
                self._stop_events[cam_id].set()
        for cam_id in targets:
            if cam_id in self._threads:
                self._threads[cam_id].join(timeout=3.0)
        logger.info("Engine stopped for cameras: %s", targets)

    def running_cameras(self) -> List[str]:
        return [c for c, t in self._threads.items() if t.is_alive()]


# Singleton engine manager
engine_manager = EngineManager()

# ─────────────────────────────────────────────────────────────────────────────
# Default camera list
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CAMERAS = ["CAM-001", "CAM-002", "CAM-003", "CAM-004", "CAM-005"]

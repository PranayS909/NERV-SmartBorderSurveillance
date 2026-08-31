from typing import List, Optional
import io
import time
import numpy as np
import cv2

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.camera import Camera
from backend.schemas.camera import CameraCreate, CameraResponse, CameraStatusUpdate

router = APIRouter(
    prefix="/api/v1/cameras",
    tags=["Cameras"]
)

# Global frame buffer for live streams (populated by VideoSource / AI Engine)
_LATEST_FRAMES = {}
_LATEST_JPEGS = {}


def set_camera_frame(camera_id: str, frame: np.ndarray):
    """Update the latest annotated frame for a camera and pre-encode JPEG once."""
    _LATEST_FRAMES[camera_id] = frame
    try:
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if success:
            _LATEST_JPEGS[camera_id] = encoded.tobytes()
    except Exception:
        pass


def get_camera_frame(camera_id: str) -> Optional[np.ndarray]:
    """Retrieve the latest annotated frame for a camera."""
    return _LATEST_FRAMES.get(camera_id)


def get_camera_jpeg(camera_id: str) -> Optional[bytes]:
    """Retrieve the latest pre-encoded JPEG bytes for a camera."""
    return _LATEST_JPEGS.get(camera_id)



def _generate_fallback_frame(camera_id: str) -> np.ndarray:
    """Generate a clean HUD placeholder frame when no live feed is feeding."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (20, 24, 28)
    
    # Grid lines
    for x in range(0, 640, 40):
        cv2.line(frame, (x, 0), (x, 480), (35, 42, 48), 1)
    for y in range(0, 480, 40):
        cv2.line(frame, (0, y), (640, y), (35, 42, 48), 1)

    # Reticle & text
    cv2.circle(frame, (320, 240), 40, (52, 217, 180), 1)
    cv2.drawMarker(frame, (320, 240), (52, 217, 180), cv2.MARKER_CROSS, 20, 1)
    
    cv2.putText(frame, f"IBVAP SENSOR: {camera_id}", (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (52, 217, 180), 2)
    cv2.putText(frame, "STANDBY / CONNECTING...", (30, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 175, 190), 1)
    
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    cv2.putText(frame, ts, (30, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 175, 190), 1)
    return frame


# ============================================================
# GET /api/v1/cameras
# ============================================================

@router.get(
    "",
    response_model=List[CameraResponse]
)
def get_cameras(
    db: Session = Depends(get_db)
):
    """List all registered surveillance cameras."""
    return db.query(Camera).order_by(Camera.camera_id).all()


# ============================================================
# GET /api/v1/cameras/{camera_id}
# ============================================================

@router.get(
    "/{camera_id}",
    response_model=CameraResponse
)
def get_camera(
    camera_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve details for a specific camera."""
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return camera


# ============================================================
# POST /api/v1/cameras
# ============================================================

@router.post(
    "",
    response_model=CameraResponse,
    status_code=201
)
def create_camera(
    camera_data: CameraCreate,
    db: Session = Depends(get_db)
):
    """Register a new camera in the database."""
    existing = db.query(Camera).filter(Camera.camera_id == camera_data.camera_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Camera '{camera_data.camera_id}' already exists")

    camera = Camera(
        camera_id=camera_data.camera_id,
        name=camera_data.name,
        location=camera_data.location,
        latitude=camera_data.latitude,
        longitude=camera_data.longitude,
        stream_url=camera_data.stream_url,
        status=camera_data.status
    )
    db.add(camera)
    try:
        db.commit()
        db.refresh(camera)
        return camera
    except Exception:
        db.rollback()
        raise


# ============================================================
# PUT /api/v1/cameras/{camera_id}/status
# ============================================================

@router.put(
    "/{camera_id}/status",
    response_model=CameraResponse
)
def update_camera_status(
    camera_id: str,
    status_data: CameraStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update camera online / offline state."""
    camera = db.query(Camera).filter(Camera.camera_id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    camera.status = status_data.status
    try:
        db.commit()
        db.refresh(camera)
        return camera
    except Exception:
        db.rollback()
        raise


# ============================================================
# GET /api/v1/cameras/{camera_id}/snapshot
# ============================================================

@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: str):
    """Get the current snapshot frame as JPEG."""
    cached_jpeg = get_camera_jpeg(camera_id)
    if cached_jpeg is not None:
        return Response(content=cached_jpeg, media_type="image/jpeg")

    frame = get_camera_frame(camera_id)
    if frame is None:
        frame = _generate_fallback_frame(camera_id)

    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode snapshot image")

    return Response(content=encoded.tobytes(), media_type="image/jpeg")


# ============================================================
# GET /api/v1/cameras/{camera_id}/stream (MJPEG)
# ============================================================

def _frame_generator(camera_id: str):
    last_jpeg = None
    fallback_bytes = None

    while True:
        raw_jpeg = get_camera_jpeg(camera_id)
        if raw_jpeg is not None and raw_jpeg is not last_jpeg:
            last_jpeg = raw_jpeg
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + raw_jpeg + b"\r\n"
            )
        elif raw_jpeg is None:
            if fallback_bytes is None:
                frame = _generate_fallback_frame(camera_id)
                success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if success:
                    fallback_bytes = encoded.tobytes()
            if fallback_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + fallback_bytes + b"\r\n"
                )
        time.sleep(0.04)  # ~25 FPS pacing


@router.get("/{camera_id}/stream")
def stream_camera(camera_id: str):
    """Live MJPEG video stream with AI detection overlays for the dashboard."""
    return StreamingResponse(
        _frame_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


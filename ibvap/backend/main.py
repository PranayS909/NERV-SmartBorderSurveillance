import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import engine, SessionLocal
from backend.models.camera import Camera
from backend.models.zone import Zone
from backend.websocket_manager import manager

from backend.api.events import router as events_router
from backend.api.cameras import router as cameras_router
from backend.api.alerts import router as alerts_router
from backend.api.zones import router as zones_router


logger = logging.getLogger("ibvap")


def _seed_initial_data():
    """Ensure baseline cameras CAM-001..CAM-005 and default zone exist."""
    db: Session = SessionLocal()
    try:
        default_cameras = [
            ("CAM-001", "BOP Main Gate", "Border Outpost Alpha", 28.6139, 77.2090),
            ("CAM-002", "Checkpost Alpha", "Checkpost Sector 1", 28.6205, 77.2165),
            ("CAM-003", "Perimeter Fence North", "Northern Perimeter", 28.6250, 77.2100),
            ("CAM-004", "Night Surveillance Post", "Observation Post Delta", 28.6180, 77.2040),
            ("CAM-005", "Secondary Transit Gate", "Transit Sector 2", 28.6110, 77.2150),
        ]
        for cam_id, name, loc, lat, lng in default_cameras:
            existing = db.query(Camera).filter(Camera.camera_id == cam_id).first()
            if not existing:
                db.add(Camera(
                    camera_id=cam_id,
                    name=name,
                    location=loc,
                    latitude=lat,
                    longitude=lng,
                    status="online"
                ))

        # Default Restricted Zone for CAM-001
        zone_01 = db.query(Zone).filter(Zone.zone_id == "ZONE-01").first()
        if not zone_01:
            db.add(Zone(
                zone_id="ZONE-01",
                name="Restricted Perimeter Area",
                zone_type="restricted",
                camera_id="CAM-001",
                polygon=[[120, 100], [600, 100], [600, 400], [120, 400]],
                severity="HIGH",
                enabled=True
            ))

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Could not complete initial data seeding: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_initial_data()

    # Start video source manager and AI engine threads
    try:
        from video.manager import video_manager
        from ai.engine import engine_manager, DEFAULT_CAMERAS
        video_manager.initialize_sources()
        engine_manager.start(DEFAULT_CAMERAS)
        logger.info("AI engine started for cameras: %s", DEFAULT_CAMERAS)
    except Exception as exc:
        logger.warning("AI engine startup failed (demo mode will still work): %s", exc)

    yield

    # Shutdown
    try:
        from ai.engine import engine_manager
        engine_manager.stop()
    except Exception:
        pass
    try:
        from video.manager import video_manager
        video_manager.release_all()
    except Exception:
        pass



app = FastAPI(
    title="IBVAP Backend",
    description="Intelligent Border Video Analytics Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(events_router)
app.include_router(cameras_router)
app.include_router(alerts_router)
app.include_router(zones_router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "IBVAP Backend",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    try:
        with engine.connect():
            return {
                "status": "healthy",
                "database": "connected"
            }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "message": str(e)
        }


# ============================================================
# Single Canonical WebSocket Endpoint: /ws/events
# ============================================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and receive ping/messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.post("/api/v1/mode")
def set_video_mode(mode: str):
    """Switch video source mode: SAMPLE or LIVE_PHONE."""
    mode = mode.upper()
    if mode not in ("SAMPLE", "LIVE_PHONE"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Use SAMPLE or LIVE_PHONE")
    try:
        from video.manager import video_manager
        video_manager.set_mode(mode)
        return {"status": "ok", "mode": mode}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@app.get("/api/v1/mode")
def get_video_mode():
    """Get current video source mode."""
    try:
        from video.manager import video_manager
        return {"mode": video_manager.mode}
    except Exception:
        return {"mode": "SAMPLE"}
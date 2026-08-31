from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.event import Event
from backend.models.alert import Alert
from backend.models.camera import Camera
from backend.models.entity import Entity
from backend.models.zone import Zone
from backend.schemas.event import EventCreate, EventResponse

from backend.websocket_manager import manager


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events"]
)


# ============================================================
# POST /api/v1/events
# ============================================================

@router.post(
    "",
    response_model=EventResponse,
    status_code=201
)
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new surveillance event, persist to PostgreSQL, create alert if high severity,
    and broadcast to connected WebSocket clients.
    """

    # Check if event already exists (Idempotency)
    existing_event = (
        db.query(Event)
        .filter(Event.event_id == event_data.event_id)
        .first()
    )

    if existing_event:
        raise HTTPException(
            status_code=409,
            detail=f"Event with event_id '{event_data.event_id}' already exists"
        )

    # Validate camera if provided
    if event_data.camera_id:
        camera = (
            db.query(Camera)
            .filter(Camera.camera_id == event_data.camera_id)
            .first()
        )

        if not camera:
            # Auto-register camera if missing so demo streams don't fail foreign key checks
            camera = Camera(
                camera_id=event_data.camera_id,
                name=f"Camera {event_data.camera_id}",
                status="online"
            )
            db.add(camera)
            try:
                db.flush()
            except Exception:
                db.rollback()

    # Validate entity if provided
    if event_data.entity_id:
        entity = (
            db.query(Entity)
            .filter(Entity.entity_id == event_data.entity_id)
            .first()
        )

        if not entity:
            # Auto-register entity so AI tracks can associate safely
            entity_type = "vehicle" if event_data.entity_id.startswith(("V-", "VEHICLE")) else "person"
            entity = Entity(
                entity_id=event_data.entity_id,
                entity_type=entity_type,
                status="active"
            )
            db.add(entity)
            try:
                db.flush()
            except Exception:
                db.rollback()

    # Validate zone if provided
    if event_data.zone_id:
        zone = (
            db.query(Zone)
            .filter(Zone.zone_id == event_data.zone_id)
            .first()
        )
        if not zone:
            # Fallback: ignore foreign key constraint violation if zone doesn't exist yet
            event_data.zone_id = None

    # Map severity to DB allowed values
    severity_val = event_data.severity.upper() if event_data.severity else "LOW"
    if severity_val not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        severity_val = "LOW"

    # Create Event record
    event = Event(
        event_id=event_data.event_id,
        event_type=event_data.event_type,
        camera_id=event_data.camera_id,
        entity_id=event_data.entity_id,
        severity=severity_val,
        confidence=event_data.confidence,
        zone_id=event_data.zone_id,
        timestamp=event_data.timestamp,
        status="NEW",
        snapshot_path=event_data.snapshot_path,
        extra_data=event_data.metadata or {}
    )
    db.add(event)
    db.flush()

    # Auto-generate Alert record for HIGH / CRITICAL events
    if severity_val in ("HIGH", "CRITICAL"):
        alert_sev = "HIGH"  # alerts table constraint allows 'LOW', 'MEDIUM', 'HIGH'
        title = f"{event_data.event_type.replace('_', ' ').title()} on {event_data.camera_id or 'Perimeter'}"
        msg = f"Triggered by {event_data.entity_id or 'unknown entity'} with confidence {event_data.confidence or 1.0:.2f}"
        
        alert = Alert(
            event_id=event.event_id,
            title=title,
            message=msg,
            severity=alert_sev,
            status="ACTIVE",
            created_at=event.timestamp or datetime.utcnow()
        )
        db.add(alert)

    try:
        db.commit()
        db.refresh(event)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database transaction failed: {str(e)}"
        )

    # Broadcast event via WebSocket after successful DB commit
    payload = {
        "type": "NEW_EVENT",
        "event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "camera_id": event.camera_id,
            "entity_id": event.entity_id,
            "severity": event.severity,
            "confidence": event.confidence,
            "zone_id": event.zone_id,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
            "status": event.status,
            "snapshot_path": event.snapshot_path,
            "metadata": event.extra_data or {}
        }
    }
    await manager.broadcast(payload)

    return event


# ============================================================
# GET /api/v1/events
# ============================================================

@router.get(
    "",
    response_model=list[EventResponse]
)
def get_events(
    camera_id: Optional[str] = Query(
        default=None,
        description="Filter events by camera ID"
    ),
    event_type: Optional[str] = Query(
        default=None,
        description="Filter events by event type"
    ),
    severity: Optional[str] = Query(
        default=None,
        description="Filter events by severity"
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter events by status"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of events to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip"
    ),
    db: Session = Depends(get_db)
):
    """
    Retrieve surveillance events newest first.
    """
    query = db.query(Event)

    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if severity:
        query = query.filter(Event.severity == severity)
    if status:
        query = query.filter(Event.status == status)

    query = query.order_by(Event.timestamp.desc())
    return query.offset(offset).limit(limit).all()
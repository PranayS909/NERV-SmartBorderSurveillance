from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.zone import Zone
from backend.schemas.zone import ZoneCreate, ZoneResponse

router = APIRouter(
    prefix="/api/v1/zones",
    tags=["Zones"]
)


# ============================================================
# GET /api/v1/zones
# ============================================================

@router.get(
    "",
    response_model=List[ZoneResponse]
)
def get_zones(
    camera_id: Optional[str] = Query(
        default=None,
        description="Filter zones by camera ID"
    ),
    enabled_only: bool = Query(
        default=True,
        description="Return only active / enabled zones"
    ),
    db: Session = Depends(get_db)
):
    """Retrieve virtual fence / restricted zone definitions."""
    query = db.query(Zone)
    if camera_id:
        query = query.filter(Zone.camera_id == camera_id)
    if enabled_only:
        query = query.filter(Zone.enabled.is_(True))

    return query.order_by(Zone.zone_id).all()


# ============================================================
# GET /api/v1/zones/{zone_id}
# ============================================================

@router.get(
    "/{zone_id}",
    response_model=ZoneResponse
)
def get_zone(
    zone_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve a specific zone definition by ID."""
    zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    return zone


# ============================================================
# POST /api/v1/zones
# ============================================================

@router.post(
    "",
    response_model=ZoneResponse,
    status_code=201
)
def create_zone(
    zone_data: ZoneCreate,
    db: Session = Depends(get_db)
):
    """Create a new virtual fence zone."""
    existing = db.query(Zone).filter(Zone.zone_id == zone_data.zone_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Zone '{zone_data.zone_id}' already exists")

    zone = Zone(
        zone_id=zone_data.zone_id,
        name=zone_data.name,
        zone_type=zone_data.zone_type,
        camera_id=zone_data.camera_id,
        polygon=zone_data.polygon,
        severity=zone_data.severity,
        enabled=zone_data.enabled
    )
    db.add(zone)
    try:
        db.commit()
        db.refresh(zone)
        return zone
    except Exception:
        db.rollback()
        raise

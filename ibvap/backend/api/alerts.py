from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.alert import Alert
from backend.schemas.alert import AlertResponse, AlertStatusUpdate

router = APIRouter(
    prefix="/api/v1/alerts",
    tags=["Alerts"]
)


# ============================================================
# GET /api/v1/alerts
# ============================================================

@router.get(
    "",
    response_model=List[AlertResponse]
)
def get_alerts(
    status: Optional[str] = Query(
        default=None,
        description="Filter alerts by status (ACTIVE, ACKNOWLEDGED, RESOLVED)"
    ),
    severity: Optional[str] = Query(
        default=None,
        description="Filter alerts by severity (LOW, MEDIUM, HIGH)"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve security alerts ordered from newest to oldest."""
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)

    query = query.order_by(Alert.created_at.desc())
    return query.offset(offset).limit(limit).all()


# ============================================================
# PUT /api/v1/alerts/{alert_id}/acknowledge
# ============================================================

@router.put(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse
)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Acknowledge an active security alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(alert)
        return alert
    except Exception:
        db.rollback()
        raise


# ============================================================
# PUT /api/v1/alerts/{alert_id}/resolve
# ============================================================

@router.put(
    "/{alert_id}/resolve",
    response_model=AlertResponse
)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Mark a security alert as resolved."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.status = "RESOLVED"
    alert.resolved_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(alert)
        return alert
    except Exception:
        db.rollback()
        raise

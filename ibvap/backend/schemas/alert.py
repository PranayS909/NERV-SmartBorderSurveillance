from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    alert_id: int
    event_id: str
    title: str
    message: Optional[str] = None
    severity: str
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(BaseModel):
    event_id: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    message: Optional[str] = None
    severity: str = Field(default="HIGH", pattern="^(LOW|MEDIUM|HIGH)$")
    status: str = "ACTIVE"


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACTIVE|ACKNOWLEDGED|RESOLVED)$")

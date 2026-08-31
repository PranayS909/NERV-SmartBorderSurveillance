from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ZoneResponse(BaseModel):
    zone_id: str
    name: str
    zone_type: str
    camera_id: Optional[str] = None
    polygon: Any
    severity: str = "HIGH"
    enabled: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ZoneCreate(BaseModel):
    zone_id: str = Field(..., max_length=30)
    name: str = Field(..., max_length=100)
    zone_type: str = Field(default="restricted", pattern="^(restricted|warning|safe|custom)$")
    camera_id: Optional[str] = Field(default=None, max_length=30)
    polygon: List[List[float]]
    severity: str = Field(default="HIGH", pattern="^(LOW|MEDIUM|HIGH)$")
    enabled: bool = True

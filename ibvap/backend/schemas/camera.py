from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CameraResponse(BaseModel):
    camera_id: str
    name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    status: str = "offline"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CameraCreate(BaseModel):
    camera_id: str = Field(..., max_length=30)
    name: str = Field(..., max_length=100)
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stream_url: Optional[str] = None
    status: str = "offline"


class CameraStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(online|offline|error)$")

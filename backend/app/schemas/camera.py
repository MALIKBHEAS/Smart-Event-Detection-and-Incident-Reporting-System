from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class CameraBase(BaseModel):
    name: str = Field(..., max_length=128)
    rtsp_url: str = Field(..., max_length=1024)
    location: Optional[str] = Field(None, max_length=255)
    enabled: bool = True
    detector_config: Optional[Dict[str, Any]] = None
    tracker_config: Optional[Dict[str, Any]] = None

    @field_validator('rtsp_url', mode='before')
    @classmethod
    def validate_rtsp_url(cls, v: Any) -> Any:
        if v is None:
            return v
        v_str = str(v).strip()
        if not v_str:
            raise ValueError("URL cannot be empty")
        
        if v_str.isdigit():
            return v_str
            
        import re
        if not re.match(r"^(rtsp|http|https)://", v_str):
            raise ValueError("Malformed URL. Must be a numeric index (e.g., '0') or a valid RTSP/HTTP URL (e.g., 'rtsp://...').")
        
        return v_str



class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    rtsp_url: Optional[str] = Field(None, max_length=1024)
    location: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    detector_config: Optional[Dict[str, Any]] = None
    tracker_config: Optional[Dict[str, Any]] = None

    @field_validator('rtsp_url', mode='before')
    @classmethod
    def validate_rtsp_url(cls, v: Any) -> Any:
        if v is None:
            return v
        v_str = str(v).strip()
        if not v_str:
            raise ValueError("URL cannot be empty")
        if v_str.isdigit():
            return v_str
        import re
        if not re.match(r"^(rtsp|http|https)://", v_str):
            raise ValueError("Malformed URL. Must be a numeric index (e.g., '0') or a valid RTSP/HTTP URL (e.g., 'rtsp://...').")
        return v_str


class CameraResponse(CameraBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

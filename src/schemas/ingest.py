from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class DetectionObject(BaseModel):
    class_: str = Field(..., alias="class")
    bbox: List[int]
    track_id: Optional[str]

class DetectionPayload(BaseModel):
    event_type_code: str
    confidence: float
    objects: Optional[List[DetectionObject]] = []

class Evidence(BaseModel):
    snapshot_url: Optional[str]
    clip_url: Optional[str]

class IngestRequest(BaseModel):
    module_id: str
    module_type: str
    timestamp: datetime
    source_device_id: str
    zone_id: int
    detection: DetectionPayload
    evidence: Optional[Evidence]
    raw: Optional[Any] = None  # preserve unknown fields

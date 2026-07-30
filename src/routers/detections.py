from fastapi import APIRouter, Depends, HTTPException, status
from ..schemas.ingest import IngestRequest
from ..core.deps import get_db, get_current_user
from ..services.ingestion_service import ingestion_service
from ..core.audit import log_action

router = APIRouter(prefix="/api/v1/detections", tags=["detections"])

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_detection(payload: IngestRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """
    Single ingestion endpoint for all detection modules.
    Idempotent: dedupe on (module_id, source_device_id, timestamp, event_type_code)
    """
    # Service handles validation against system_modules and event_types and writes raw candidate
    try:
        event = await ingestion_service.handle_ingest(db, payload)
    except ingestion_service.DuplicateIngestException:
        # idempotent: return 200 with existing or 204
        raise HTTPException(status_code=200, detail="Duplicate detection within dedupe window; ignored.")
    await log_action(db, user.user_id, "ingest", "ingests", None, {"module": payload.module_id, "zone": payload.zone_id})
    return {"status": "accepted", "event": event}

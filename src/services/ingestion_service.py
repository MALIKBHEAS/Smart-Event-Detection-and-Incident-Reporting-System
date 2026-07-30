from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.all_models import SystemModule, EventType, Event, EventEvidence
from ..schemas.ingest import IngestRequest
from ..core.config import settings

class DuplicateIngestException(Exception):
    pass

class IngestionService:
    async def handle_ingest(self, db: AsyncSession, payload: IngestRequest):
        # basic validation: module must exist and enabled
        stmt = select(SystemModule).where(SystemModule.module_code == payload.module_id)
        res = await db.execute(stmt)
        module = res.scalars().first()
        if not module or not module.is_enabled:
            raise ValueError("Module unknown or disabled")

        # dedupe: check for existing event candidate within dedupe window
        window_start = payload.timestamp - timedelta(seconds=settings.DEDUPE_WINDOW_SECONDS)
        stmt2 = select(Event).where(
            Event.module_id == module.module_id,
            Event.detected_at >= window_start,
            Event.detected_at <= payload.timestamp,
            Event.raw_payload['detection']['event_type_code'].astext == payload.detection.event_type_code,
            Event.raw_payload['source_device_id'].astext == payload.source_device_id
        )
        res2 = await db.execute(stmt2)
        existing = res2.scalars().first()
        if existing:
            raise DuplicateIngestException()

        # insert raw pending event candidate row (status='candidate') for fusion worker to consume
        ev = Event(
            event_type_id=None,  # resolved by fusion engine
            module_id=module.module_id,
            zone_id=payload.zone_id,
            camera_id=None,
            sensor_id=None,
            detected_at=payload.timestamp,
            confidence=payload.detection.confidence,
            severity=None,
            status="candidate",
            description=None,
            raw_payload=payload.model_dump(),  # full payload for fusion
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)

        # store evidence placeholders
        if payload.evidence:
            e = EventEvidence(event_id=ev.event_id, evidence_type="snapshot", file_url=payload.evidence.snapshot_url)
            db.add(e)
            await db.commit()

        # publish to queue for fusion engine or have fusion consume DB candidate rows
        # For now we assume fusion reads event candidates from DB or we can publish a simple message to RabbitMQ
        return {"candidate_id": ev.event_id, "status": ev.status}

ingestion_service = IngestionService()

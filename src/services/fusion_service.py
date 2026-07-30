"""
Fusion engine logic (consumes candidates and creates canonical events).
This module is intended for the fusion worker process (workers/fusion_worker.py).
It does NOT contain detection logic; all thresholds come from detection_rules table.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta, datetime
from ..models.all_models import Event, DetectionRule, EventType, WhitelistDevice

class FusionService:
    DEDUPE_WINDOW_SECONDS = 30

    async def process_candidate(self, db: AsyncSession, candidate_event: Event):
        # 1. group by zone/time window: find corroborating candidates
        window_start = candidate_event.detected_at - timedelta(seconds=self.DEDUPE_WINDOW_SECONDS)
        stmt = select(Event).where(
            Event.zone_id == candidate_event.zone_id,
            Event.detected_at >= window_start,
            Event.detected_at <= candidate_event.detected_at,
            Event.status == "candidate"
        )
        res = await db.execute(stmt)
        group = res.scalars().all()

        # 2. determine event_type_code from raw_payload detection.event_type_code
        et_code = candidate_event.raw_payload.get("detection", {}).get("event_type_code")
        # lookup EventType
        stmt_et = select(EventType).where(EventType.type_code == et_code)
        res_et = await db.execute(stmt_et)
        et = res_et.scalars().first()
        if not et:
            # unknown event type -> log and drop or mark unknown
            candidate_event.status = "unknown_event_type"
            await db.commit()
            return None

        # 3. Find detection rules for this module/event/zone
        stmt_rules = select(DetectionRule).where(
            DetectionRule.event_type_id == et.event_type_id,
            DetectionRule.zone_id == candidate_event.zone_id,
            DetectionRule.is_active == True
        )
        res_rules = await db.execute(stmt_rules)
        rules = res_rules.scalars().all()

        # Evaluate rules (if none active, default pass with base severity)
        # Rules include min_confidence, baseline_required, min_rssi_threshold etc.
        passed = False
        for r in rules:
            # Check confidence
            if candidate_event.confidence is not None and float(candidate_event.confidence) < float(r.min_confidence or 0):
                continue
            # Check baseline requirement: here we'd ensure no active baseline requirement blocks (omitted detail)
            # Additional checks for RSSI/dwell require cross data from network_device_sightings or candidate_event.raw_payload
            passed = True
            break

        if not passed:
            candidate_event.status = "rejected_by_rule"
            await db.commit()
            return None

        # 4. cross-check whitelists
        mac = candidate_event.raw_payload.get("raw", {}).get("mac_address")
        if mac:
            stmt_w = select(WhitelistDevice).where(WhitelistDevice.mac_address == mac, WhitelistDevice.is_active == True)
            res_w = await db.execute(stmt_w)
            if res_w.scalars().first():
                candidate_event.status = "suppressed_whitelist"
                await db.commit()
                return None

        # 5. compute severity: combine event type default + zone risk + corroboration boost
        zone_risk = 1
        try:
            zone_risk = candidate_event.raw_payload.get("zone_risk", zone_risk)
        except Exception:
            pass
        final_severity = int(et.default_severity or 1) + int(zone_risk)
        if len(group) >= 2:
            final_severity += 1  # corroboration boost

        # 6. create canonical event (update candidate row)
        candidate_event.event_type_id = et.event_type_id
        candidate_event.severity = final_severity
        candidate_event.status = "open"
        candidate_event.created_at = datetime.utcnow()
        await db.commit()
        # publish to alert dispatch (not implemented here)
        return candidate_event

fusion_service = FusionService()

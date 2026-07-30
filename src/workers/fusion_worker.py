import asyncio
import aio_pika
import json
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import AsyncSessionLocal
from ..services.fusion_service import fusion_service
from ..core.config import settings
from ..models.all_models import Event
from sqlalchemy import select

async def consume():
    # Option A: consume messages from RabbitMQ
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    q = await channel.declare_queue("detections", durable=True)

    async with q.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                payload = json.loads(message.body)
                # payload contains candidate event id
                candidate_id = payload.get("candidate_id")
                async with AsyncSessionLocal() as db:
                    stmt = select(Event).where(Event.event_id == candidate_id)
                    res = await db.execute(stmt)
                    candidate = res.scalars().first()
                    if candidate and candidate.status == "candidate":
                        await fusion_service.process_candidate(db, candidate)

if __name__ == "__main__":
    asyncio.run(consume())

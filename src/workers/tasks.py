from ..celery_app import celery_app
from ..db.session import AsyncSessionLocal
from ..services import devices_service, network_service, events_service, rules_service
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

@celery_app.task(name="tasks.health_check_devices")
def health_check_devices():
    # synchronous wrapper calling async implementation
    asyncio.run(_health_check())

async def _health_check():
    async with AsyncSessionLocal() as db:
        await devices_service.health_check_devices(db)

@celery_app.task(name="tasks.compute_daily_stats")
def compute_daily_stats():
    asyncio.run(_compute_daily_stats())

async def _compute_daily_stats():
    async with AsyncSessionLocal() as db:
        await network_service.compute_daily_stats(db)

@celery_app.task(name="tasks.compute_recurring_score")
def compute_recurring_score():
    asyncio.run(_compute_recurring_score())

async def _compute_recurring_score():
    async with AsyncSessionLocal() as db:
        await network_service.compute_recurring_score(db)

@celery_app.task(name="tasks.escalation_policy_check")
def escalation_policy_check():
    asyncio.run(_escalation_check())

async def _escalation_check():
    async with AsyncSessionLocal() as db:
        await events_service.escalation_policy_check(db)

# SEDIRS (Smart Event Detection & Incident Reporting System)

This repository contains the backend scaffold for SEDIRS implemented with FastAPI, async SQLAlchemy, Pydantic v2, Celery, RabbitMQ, Redis and MinIO-compatible S3.

See the src/ directory for the application. The scaffold includes models, schemas, routers, services, workers, Celery tasks, and tests.

Quickstart (development):
1. Create a .env file with DATABASE_URL, REDIS_URL, RABBITMQ_URL, JWT_SECRET, and S3 credentials.
2. docker-compose up --build
3. Run alembic upgrade head (or use metadata.create_all for initial dev)
4. Start the fusion worker: docker-compose run fusion_worker

Security & privacy:
- Face embeddings must be encrypted at rest. Implement application-level encryption (KMS + Fernet) or use pgcrypto.
- Audit logs are written by state-changing endpoints via core.audit.log_action.

Architecture:
- Detection modules are external and POST to /api/v1/detections/ingest.
- Fusion engine runs separately and consumes candidate events via RabbitMQ or DB.

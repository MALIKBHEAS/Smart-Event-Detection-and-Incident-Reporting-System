# Docker

Two profiles: `dev` (hot reload, source bind-mounted) and `prod` (built
images, nginx serving the frontend). Both use a Postgres database.

## Quick start (development)

```bash
cp .env.example .env
docker compose --profile dev up --build
```

- Frontend (Vite dev server, HMR): http://localhost:5173
- Backend (FastAPI, auto-reload): http://localhost:8000
- Postgres: localhost:5432 (credentials from `.env`)

Source directories are bind-mounted, so edits to `backend/` or `frontend/`
apply live without rebuilding the image. Alembic migrations run
automatically on backend container start (see `docker/backend-entrypoint.sh`).

## Production

```bash
cp .env.example .env   # edit POSTGRES_PASSWORD etc. first
docker compose --profile prod up --build -d
```

- Frontend: http://localhost (nginx serving the built SPA, proxying `/api/*`
  to the backend -- see `docker/frontend-nginx.conf`)
- Backend: http://localhost:8000

## What's in `docker/`

| File | Purpose |
|---|---|
| `backend.Dockerfile` | Multi-stage: `base` (deps) -> `dev` (adds test/lint tooling, reload) -> `production` (minimal, single worker) |
| `frontend.Dockerfile` | Multi-stage: `dev` (Vite dev server) -> `build` (production bundle) -> `production` (nginx) |
| `backend-entrypoint.sh` | Runs `alembic upgrade head` before starting the server -- see note below |
| `frontend-nginx.conf` | Serves the SPA + proxies `/api/*` to the backend, mirroring the Vite dev proxy so the frontend code is identical in dev and prod |

## Health checks

Both `backend-*` and `frontend-prod` have Docker `HEALTHCHECK`s
(`/health` for the backend, `/` for the frontend). `db` uses `pg_isready`.
`backend-*` won't start until `db` reports healthy.

## Volumes

- `db-data`: Postgres data directory (persists across restarts)
- `evidence-data`: mounted at `/srv/backend/evidence` -- detection
  snapshots/clips survive container recreation
- `frontend-node-modules`: dev-only, keeps the container's `node_modules`
  from being shadowed by the host bind mount

## Known limitations (read before relying on this in production)

- **Not build-tested against a live Docker daemon.** This sandbox has no
  Docker available, so the Dockerfiles/compose file are syntax-validated
  and the dependency set + Alembic migrations were verified in an isolated
  Python venv, but the actual `docker build`/`docker compose up` was never
  executed end-to-end. Please run it once locally and report any build
  error.
- **Alembic migration bug fixed along the way**: `0001_initial.py` had a
  duplicate `ix_events_type` index (once from `Column(index=True)`, once
  from an explicit `op.create_index`), which made `alembic upgrade head`
  fail on any *fresh* database -- harmless against the existing `dev.db`
  (which predates strict migration history) but would have broken
  Postgres-from-scratch, i.e. every Docker `prod`/`dev` run. Fixed by
  removing the duplicate explicit call.
- **Migration `0002` isn't SQLite-batch-safe** (`op.create_foreign_key`
  outside `batch_alter_table`, which SQLite doesn't support for adding
  constraints). This only matters if you point `DATABASE_URL` at SQLite
  and run migrations from scratch -- Postgres (what Docker uses) handles it
  fine. Continue using the existing `dev.db` snapshot for local
  non-Docker SQLite development, or migrate that specific revision to
  batch mode if you need a from-scratch SQLite path later.
- **Backend production image runs as root**, not a dropped-privilege user.
  A non-root user needs the entrypoint to `chown` the Docker-created
  `evidence-data` volume at container start (it's root-owned by default);
  that fix needs a live daemon to verify, so it's left as a documented
  follow-up rather than shipped unverified.
- **YOLO inference isn't installed by default** (`requirements.txt`
  deliberately excludes `torch`/`ultralytics` -- see `requirements-yolo.txt`).
  Install it separately in the image if you need real object detection
  rather than the pipeline scaffolding.
- **GPU passthrough isn't configured.** If you install the YOLO
  dependencies and want GPU inference, you'll need to add
  `deploy.resources.reservations.devices` (NVIDIA runtime) to the backend
  service yourself.

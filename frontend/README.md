# Sentry Deck — Frontend

React + TypeScript + Vite console for the Smart Event Detection backend.

Implements only what the current backend actually exposes:

| Page | Endpoints used |
|---|---|
| Login | none (local mock session only — backend has no auth yet) |
| Dashboard | `GET /health`, `GET /health/workers`, `GET /cameras` |
| Camera Management | `GET/POST/PUT/DELETE /cameras` |
| Worker Control | `GET /health/workers`, `POST /workers/start/{id}`, `POST /workers/stop/{id}` |
| Health Monitoring | `GET /health`, `GET /health/workers` |
| Events / Incidents / Reports / Notifications | none — routed placeholder pages, clearly marked "Coming soon" until the backend implements them |

No endpoints are invented and no requests are made from the placeholder pages.

## Running locally

```bash
cd frontend
npm install
cp .env.example .env   # optional, defaults already work
npm run dev
```

This starts Vite on `http://localhost:5173`. The dev server proxies
`/api/*` to `http://localhost:8000` (your locally-running backend) and
strips the `/api` prefix, since the backend does not send CORS headers.
Start the backend separately (see `backend/README.md` if present, or
`uvicorn app.main:app --reload` from `backend/`).

To point the dev proxy at a different backend port/host:

```bash
VITE_BACKEND_ORIGIN=http://localhost:9000 npm run dev
```

## Building

```bash
npm run build
```

Type-checks (`tsc -b`) then builds to `dist/`. In production, serve `dist/`
behind a reverse proxy that forwards `/api/*` to the backend (or set
`VITE_API_BASE_URL` at build time to the backend's public URL if it has
CORS enabled separately).

## Notes

- Login is a **local-only mock**: any name is accepted, nothing is sent to
  the server, and it only gates the UI. Swap `src/auth` for real auth once
  the backend has a login endpoint.
- Dashboard/Health/Worker pages poll on an interval (5–20s) rather than
  using a websocket, since the backend doesn't currently expose one for
  this data.

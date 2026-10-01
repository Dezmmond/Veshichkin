# Veshichkin

Veshichkin is a project for managing a personal wardrobe and its inventory. It is currently at the Stage 1 foundation stage; product functionality is not implemented yet.

## Repository layout

- `backend/` — Python backend; dependencies are managed with `uv`.
- `frontend/` — Vue frontend; dependencies are managed with `npm`.

## Prerequisites

- Python 3.12 or 3.13 and `uv`.
- Node.js 22 and npm (matching the Docker frontend build).
- Docker and Docker Compose for the production-like local deployment.
- A PostgreSQL database accessible from the host for backend development.

## Backend development

Use Python 3.12 or 3.13 and `uv`. From the repository root:

```bash
uv sync --locked --directory backend
export VESHICHKIN_DATABASE_URL='postgresql+psycopg://veshichkin@localhost:5432/veshichkin'
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn veshichkin.main:app --reload
```

The database URL above is also the development default; it contains no password.
Provide credentials through the environment when your PostgreSQL setup requires them.
Only the `postgresql+psycopg` scheme is supported (synchronous Psycopg 3).
For this development workflow, provision PostgreSQL separately and create the
database and role matching the URL before applying migrations. The Compose
deployment below is a separate complete runtime; its database does not publish
a host port, so this localhost URL does not connect to Compose PostgreSQL.

Settings use the `VESHICHKIN_` prefix: `APPLICATION_NAME` (default `Veshichkin`),
`ENVIRONMENT` (default `development`), `DEBUG` (default `false`), `DATABASE_URL`,
and `STATIC_DIR` (unset by default; enables serving a built SPA).

- Liveness: http://127.0.0.1:8000/api/health — returns HTTP 200 without database access.
- Readiness: http://127.0.0.1:8000/api/ready — executes `SELECT 1`; returns HTTP 200
  when PostgreSQL is available, or HTTP 503 with a safe JSON error when unavailable.

Database connection and pool wait timeouts are each 3 seconds; no connection retries
are performed in the endpoint. Development FastAPI startup does not connect to
PostgreSQL; the Docker startup command applies migrations before starting FastAPI.
SQLAlchemy checks pooled connections before reuse so a PostgreSQL restart does
not leave a stale connection for the next request.

## API contract generation

With backend and frontend dependencies installed, run:

```bash
cd frontend
npm run api:generate
```

The flow is FastAPI OpenAPI → `openapi.json` → TypeScript types.
This exports FastAPI OpenAPI to `frontend/openapi.json` and generates
`frontend/src/api/generated/schema.d.ts` with `openapi-typescript`.
No running backend server or PostgreSQL is required. Regenerate after API changes;
do not edit generated types manually.

## Frontend development

With the backend above running, start Vite in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. The typed browser client uses relative
`/api/...` URLs on the current origin. Home shows a technical backend status using
`/api/health`, which works without PostgreSQL. No backend CORS configuration is required.

## Tests and quality

Backend, from the repository root:

```bash
cd backend
uv run pytest
uv run ruff check src tests alembic
uv run mypy src
```

Frontend, from the repository root in another terminal:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

## Production-like local deployment

From the repository root, with Docker and Docker Compose installed:

```bash
docker compose up --build
```

Open http://localhost:8000. One app container serves the built Vue SPA and FastAPI
on the same origin under `/api`. PostgreSQL 17 stores data in the `postgres_data`
named volume and does not publish a host port. The app waits for healthy PostgreSQL,
runs `alembic upgrade head`, then starts uvicorn. The Compose credentials are
development-only local defaults, not a production secret-management solution.

Stop containers while retaining database data:

```bash
docker compose down
```

**Warning:** `docker compose down -v` deletes the local database volume and its data.

One-off migration commands override the app startup command:

```bash
docker compose run --rm app alembic current
```

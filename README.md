# Veshichkin

Veshichkin is a project for managing a personal wardrobe and its inventory. It is currently at the Stage 1 foundation stage; product functionality is not implemented yet.

## Repository layout

- `backend/` — Python backend; dependencies are managed with `uv`.
- `frontend/` — Vue frontend; dependencies are managed with `npm`.

## Backend development

Use Python 3.12 or 3.13 and `uv`. From the repository root:

```bash
uv sync --locked --directory backend
export VESHICHKIN_DATABASE_URL='postgresql+psycopg://veshichkin@localhost:5432/veshichkin'
uv run --directory backend uvicorn veshichkin.main:app --reload
```

The database URL above is also the development default; it contains no password.
Provide credentials through the environment when your PostgreSQL setup requires them.
Only the `postgresql+psycopg` scheme is supported (synchronous Psycopg 3).
PostgreSQL must be provisioned separately; Docker Compose is not implemented yet.

Settings use the `VESHICHKIN_` prefix: `APPLICATION_NAME` (default `Veshichkin`),
`ENVIRONMENT` (default `development`), `DEBUG` (default `false`), and `DATABASE_URL`.

- Liveness: http://127.0.0.1:8000/api/health — returns HTTP 200 without database access.
- Readiness: http://127.0.0.1:8000/api/ready — executes `SELECT 1`; returns HTTP 200
  when PostgreSQL is available, or HTTP 503 with a safe JSON error when unavailable.

Database connection and pool wait timeouts are each 3 seconds; no connection retries
are performed in the endpoint. Application startup does not connect to PostgreSQL.

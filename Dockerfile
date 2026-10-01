FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src/ ./src/
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python

FROM python:3.12-slim AS runtime
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VESHICHKIN_STATIC_DIR=/app/static
WORKDIR /app/backend
COPY --from=backend-build /app/backend/.venv ./.venv
COPY backend/alembic.ini ./
COPY backend/alembic/ ./alembic/
COPY --from=frontend-build /build/frontend/dist /app/static
COPY docker/start.sh /app/start.sh
EXPOSE 8000
CMD ["sh", "/app/start.sh"]

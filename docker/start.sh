#!/bin/sh
set -eu

alembic upgrade head
exec uvicorn veshichkin.main:app --host 0.0.0.0 --port 8000

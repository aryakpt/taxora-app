#!/bin/sh
# Container entrypoint: bring the database and storage up to date, then serve.
# Migrations run here because the host has no pre-deploy step. That is safe with one instance (a free Space
# runs one); with several, move this to a pre-deploy step so two never migrate at once.
set -e
alembic upgrade head
python -m app.cli prepare-storage
# One worker: rate limits and background ingestion jobs live in this process (see core/rate_limit.py).
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-server-header

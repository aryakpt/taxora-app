BACKEND := backend
PY := $(BACKEND)/.venv/bin/python

.PHONY: help db-up db-down db-reset install migrate api web test lint set-role

help:  ## List available commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

db-up:  ## Start PostgreSQL + pgvector (Docker) and wait until it is ready
	docker compose up -d --wait db

db-down:  ## Stop PostgreSQL (data is kept)
	docker compose down

db-reset:  ## Delete local database data and start fresh
	docker compose down -v && docker compose up -d --wait db

install:  ## Create the backend virtualenv and install backend + frontend dependencies
	test -d $(BACKEND)/.venv || python3 -m venv $(BACKEND)/.venv
	$(PY) -m pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm ci

migrate:  ## Apply database migrations
	cd $(BACKEND) && .venv/bin/alembic upgrade head

api:  ## Run the API with auto-reload on http://localhost:8000
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

web:  ## Run the frontend dev server on http://localhost:5173
	cd frontend && npm run dev

test:  ## Run backend tests (DB tests are skipped if the database is not running)
	cd $(BACKEND) && .venv/bin/pytest

set-role:  ## Change a user's role, e.g. make set-role EMAIL=you@example.com ROLE=admin
	@test -n "$(EMAIL)" -a -n "$(ROLE)" || (echo "usage: make set-role EMAIL=<email> ROLE=<user|reviewer|admin>" && exit 1)
	cd $(BACKEND) && .venv/bin/python -m app.cli set-role "$(EMAIL)" "$(ROLE)"

lint:  ## Lint backend code
	cd $(BACKEND) && .venv/bin/ruff check app tests

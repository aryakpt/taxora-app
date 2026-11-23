BACKEND := backend
PY := $(BACKEND)/.venv/bin/python

.PHONY: help db-up db-down db-reset install migrate api web test lint check set-role seed ask-raw eval eval-draft reprocess reindex \
	prod prod-migrate deploy-render-env deploy-render deploy-status deploy-web

help:  ## List available commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

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

seed:  ## Create dev accounts (admin/reviewer/user@example.com); refuses when APP_ENV=production
	cd $(BACKEND) && .venv/bin/python -m app.cli seed-dev-users

ask-raw:  ## Ask the LLM directly, without sources or guards (baseline): make ask-raw Q="..."
	@test -n "$(Q)" || (echo 'usage: make ask-raw Q="pertanyaan"' && exit 1)
	cd $(BACKEND) && .venv/bin/python -m app.cli ask-raw "$(Q)"

eval:  ## Score scope guard + retrieval on the evaluation dataset (published documents)
	cd $(BACKEND) && .venv/bin/python -m app.cli eval-retrieval

eval-draft:  ## Same, also searching documents still under review
	cd $(BACKEND) && .venv/bin/python -m app.cli eval-retrieval --include-unreviewed

reindex:  ## Embed chunks that have no vector (after an embedding model change); safe to rerun, it continues
	cd $(BACKEND) && .venv/bin/python -m app.cli reindex

reprocess:  ## Re-extract a document still under review with the current extractor: make reprocess JOB=<id>
	@test -n "$(JOB)" || (echo 'usage: make reprocess JOB=<job id>' && exit 1)
	cd $(BACKEND) && .venv/bin/python -m app.cli reprocess "$(JOB)"

lint:  ## Lint backend code
	cd $(BACKEND) && .venv/bin/ruff check app tests

check:  ## Everything CI runs: lint, all tests (database required), frontend build
	cd $(BACKEND) && .venv/bin/ruff check .
	cd $(BACKEND) && REQUIRE_TEST_DATABASE=1 .venv/bin/pytest -q
	cd frontend && npm run build

# --- Production: settings from deploy/.env.production (README "Deployment") ------------------------------

PROD := cd $(BACKEND) && .venv/bin/python ../deploy/prodenv.py

prod:  ## Run an app.cli command against production, e.g. make prod CMD="set-role you@x.com admin"
	$(PROD) .venv/bin/python -m app.cli $(CMD)

prod-migrate:  ## Apply database migrations to production
	$(PROD) .venv/bin/alembic upgrade head

deploy-render-env:  ## Send the API's secrets to Render, then redeploy
	cd deploy && ../$(PY) render.py env

deploy-render:  ## Redeploy the API on Render (latest commit of its branch)
	cd deploy && ../$(PY) render.py deploy

deploy-status:  ## The API's URL and its latest deploys on Render
	cd deploy && ../$(PY) render.py status

deploy-web:  ## Build and deploy the frontend to Vercel production
	cd deploy && ../$(PY) vercel.py

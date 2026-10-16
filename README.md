# Taxora

Taxora is an evidence-first assistant for questions about Indonesian PPh and PPN. The existing backend is a Python/FastAPI API; the web client is a React + TypeScript application built with Vite. The PRD is the product specification. This implementation pass focuses on the frontend and wires it to the existing API rather than substituting local sample answers.

## Repository architecture

- `backend/` — FastAPI routes, SQLAlchemy models, retrieval, ingestion, and AI provider adapter.
- `frontend/` — React/TypeScript client organized around three page features and routed with React Router (`/`, `/regulations`, `/admin`). `src/router/AppRouter.tsx` owns the route table and `src/App.tsx` composes the application; `src/features/` contains only `tax-assistant/`, `regulation-library/`, and `knowledge-admin/`, each organized into `pages/` and only the supporting `api/`, `hooks/`, or `components/` layers it needs; `src/shared/` contains cross-feature API infrastructure, application-shell components, domain types, and global Sass design tokens/styles.
- `docker-compose.yml`, `Dockerfile`, `alembic.ini` — existing backend/database runtime configuration.
- `prd.md` — complete product requirements document.

## Requirements

- Node.js 20+ and npm
- Python 3.11+
- PostgreSQL with pgvector (use the provided Docker Compose configuration)
- An OpenAI API key for model-backed answers; credentials are not required to build the frontend

## Configure and run

1. Copy `.env.example` to `.env` and set distinct `API_TOKEN` and `ADMIN_TOKEN` values. Set `OPENAI_API_KEY` to enable answer generation. Keep secrets out of source control.
2. Start PostgreSQL: `docker compose up -d db` (check the service name in `docker-compose.yml` if your Compose setup uses a different target).
3. Install Python dependencies: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
4. Apply migrations: `alembic upgrade head`.
5. Start the API from the repository root: `uvicorn backend.main:app --reload --port 8000`.
6. In another terminal, run `cd frontend && npm install`, then from the repository root run `npm run dev` (or `cd frontend && npm run dev`).
7. Open the Vite URL (normally `http://localhost:5173`). Select the profile/settings control and enter the configured `API_TOKEN`. Use `ADMIN_TOKEN` for admin ingestion actions.

Set `VITE_API_URL` in `frontend/.env.local` to override the API origin (default `http://localhost:8000`), for example `VITE_API_URL=http://localhost:8000`. The backend's `FRONTEND_ORIGIN` must match the browser origin; set it to `http://localhost:5173` for the default Vite server, then restart the API.

## Frontend commands

From the repository root (after installing frontend dependencies):

- `npm run dev` — start Vite's local development server
- `npm run build` — run TypeScript validation and create the production build
- `npm run preview` — serve the production build locally

The same scripts are available directly inside `frontend/`.

## Current frontend scope and limitations

- The chat sends requests to `POST /api/v1/chat`, shows real loading and API error states, passes optional tax period and taxpayer context, renders evidence citations/official links from the response, and submits feedback to the existing endpoint.
- The frontend supports English and Indonesian UI copy. The selected language persists in the browser and is sent with chat requests so generated answers and backend insufficient-evidence messages use the chosen language. Legal quotations and regulation titles remain in their source language.
- `POST /api/v1/chat` accepts `response_language: "en" | "id"` (defaults to Indonesian for existing clients); the selected value is retained in message metadata.
- Conversation list/detail, published regulation listing, and administrator ingestion routes are connected to the backend. The UI does not invent regulations, sources, or successful answers.
- The frontend is English-language as requested; the PRD's generation behavior and jurisdiction are Indonesian. Questions can be written in Indonesian or English, but model output follows the backend prompt configuration.
- Backend conversation detail currently returns message content and metadata but not source records; therefore reloaded history cannot restore citation cards or per-message feedback state. A successful chat fetches its assistant message ID for feedback because the chat response returns a request ID rather than message ID.
- The current API's authentication is a development bearer-token mechanism. It is not a production OIDC implementation. The browser stores the configured API token in local storage; deploy only over HTTPS and use an appropriate production identity flow before public release.
- Backend upload currently rejects document uploads after validation, and the ingestion endpoint processes synchronously. This frontend exposes URL ingestion only, matching the functional endpoint available now.
- Ingestion status is visible in the admin screen, but approval/publication actions, audit history, evaluation results, and regulation-version editing are not yet exposed in the frontend.
- The source library contains only published regulations returned by the backend; it does not seed sample legal data. No evaluation scores or verified legal coverage are claimed.
- The backend returns an unavailable evaluation status until a reviewed evaluation dataset exists. Backend migrations, RAG quality, legal verification, production auth, and broader PRD features remain backend work and are not represented as frontend-complete.

## Backend checks

Run backend tests with `pytest` after installing Python dependencies. For production, configure PostgreSQL, apply Alembic migrations, set a non-development token and provider credentials, and perform the PRD's separate security, legal-source, and evaluation reviews.

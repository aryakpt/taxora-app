# Taxora

Taxora is an evidence-first assistant for questions about Indonesian PPh and PPN. The existing backend is a Python/FastAPI API; the web client is a React + TypeScript application built with Vite. The PRD is the product specification. This implementation pass focuses on the frontend and wires it to the existing API rather than substituting local sample answers.

## Repository architecture

- `backend/` — FastAPI application, its `.env.example`, Python requirements, `.venv`, Alembic configuration/migrations, and backend tests.
- `frontend/` — React/TypeScript client with its own `.env.example`, organized around three page features and routed with React Router (`/`, `/regulations`, `/admin`). `src/router/AppRouter.tsx` owns the route table and `src/App.tsx` composes the application; `src/features/` contains only `tax-assistant/`, `regulation-library/`, and `knowledge-admin/`, each organized into `pages/` and only the supporting `api/`, `hooks/`, or `components/` layers it needs; `src/shared/` contains account authentication, cross-feature API infrastructure, application-shell components, domain types, and global Sass design tokens/styles.
- `frontend/package.json` — frontend dependencies and commands.
- `prd.md` — complete product requirements document.

## Requirements

- Node.js 20+ and npm
- Python 3.11+
- PostgreSQL 16 with the pgvector extension
- An OpenAI API key for model-backed answers; credentials are not required to build the frontend

## Configure and run

1. Install PostgreSQL 16 locally and install the pgvector extension compatible with that PostgreSQL installation. Create a database and enable the extension in it with `CREATE EXTENSION vector;`. The migration also enables the extension, but the pgvector files must already be installed on the PostgreSQL server.
2. Copy `backend/.env.example` to `backend/.env`. Set `DATABASE_URL` to your local PostgreSQL credentials, and replace `AUTH_SECRET_KEY` and `ADMIN_TOKEN` with long random values. Set `OPENAI_API_KEY` to enable answer generation. The OpenAI key stays on the backend and is never entered by end users or exposed to Vite.
3. From the repository root, create a Python environment and install backend dependencies:

   ```powershell
   py -m venv backend\.venv
   backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```

4. Apply database migrations from the repository root:

   ```powershell
   backend\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
   ```

5. Start the API from the repository root:

   ```powershell
   backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
   ```

6. In another terminal, install and start the frontend from `frontend/`:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

7. Open the Vite URL (normally `http://localhost:5173`) and create a user account or sign in with email and password. User sessions use an HTTP-only cookie. Set `AUTH_COOKIE_SECURE=true` in HTTPS deployments.

Set `VITE_API_URL` in `frontend/.env.local` to override the API origin (default `http://localhost:8000`), for example `VITE_API_URL=http://localhost:8000`. The backend's `FRONTEND_ORIGIN` must match the browser origin; set it to `http://localhost:5173` for the default Vite server, then restart the API. For production, use frontend/API hosts under the same site (for example `app.example.com` and `api.example.com`) with HTTPS and `AUTH_COOKIE_SECURE=true` so the `SameSite=Lax` session cookie is sent correctly.

## Frontend commands

From `frontend/` (after installing frontend dependencies):

- `npm run dev` — start Vite's local development server
- `npm run build` — run TypeScript validation and create the production build
- `npm run preview` — serve the production build locally

Deployment and CI/CD are not configured yet. When a hosting platform is chosen, configure `VITE_API_URL` for the frontend and `FRONTEND_ORIGIN` for the API to match the deployed origins.

## Current frontend scope and limitations

- The chat sends requests to `POST /api/v1/chat`, shows real loading and API error states, passes optional tax period and taxpayer context, renders evidence citations/official links from the response, and submits feedback to the existing endpoint.
- The frontend supports English and Indonesian UI copy. The selected language persists in the browser and is sent with chat requests so generated answers and backend insufficient-evidence messages use the chosen language. Legal quotations and regulation titles remain in their source language.
- Standalone email/password registration and sign-in are implemented. Passwords are hashed with Argon2id; browser sessions use signed, HTTP-only cookies. New accounts receive the `user` role. An administrator can grant an account the `admin` role directly in PostgreSQL; Google OAuth, email verification, password reset, and auth rate limiting are not implemented yet.
- To grant admin access to an account that has registered, run `UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';` against PostgreSQL, then sign out and sign back in.
- `POST /api/v1/chat` accepts `response_language: "en" | "id"` (defaults to Indonesian for existing clients); the selected value is retained in message metadata.
- Conversation list/detail, published regulation listing, and administrator ingestion routes are connected to the backend. The UI does not invent regulations, sources, or successful answers.
- Backend conversation detail currently returns message content and metadata but not source records; therefore reloaded history cannot restore citation cards or per-message feedback state. A successful chat fetches its assistant message ID for feedback because the chat response returns a request ID rather than message ID.
- The `OPENAI_API_KEY` is a server-side provider credential configured by the application operator. Users do not supply provider keys. Authentication currently uses first-party email/password accounts; use HTTPS, secure cookies, rate limiting, and a security review before public launch.
- Backend upload currently rejects document uploads after validation, and the ingestion endpoint processes synchronously. This frontend exposes URL ingestion only, matching the functional endpoint available now.
- Ingestion status is visible in the admin screen, but approval/publication actions, audit history, evaluation results, and regulation-version editing are not yet exposed in the frontend.
- The source library contains only published regulations returned by the backend; it does not seed sample legal data. No evaluation scores or verified legal coverage are claimed.
- The backend returns an unavailable evaluation status until a reviewed evaluation dataset exists. RAG quality, legal verification, production auth hardening, and broader PRD features remain incomplete.

## Backend checks

Run backend tests with `backend/.venv/bin/pytest -c backend/pytest.ini`. For production, configure PostgreSQL, apply `backend/alembic.ini` migrations, set a strong `AUTH_SECRET_KEY`, enable secure cookies, configure provider credentials, and perform the PRD's separate security, legal-source, and evaluation reviews.

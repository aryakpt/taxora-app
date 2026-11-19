# Taxora

Taxora is an evidence-first assistant for questions about Indonesian PPh and PPN. The existing backend is a Python/FastAPI API; the web client is a React + TypeScript application built with Vite. The PRD is the product specification. Work proceeds in vertical slices; see `prd.md` for the specification.

## Repository architecture

```text
taxora-app/
├── backend/                 # FastAPI API (Python)
│   ├── app/
│   │   ├── main.py          # app factory: middleware, routers, /api/v1/health
│   │   ├── models.py        # imports every module's models (Alembic, tests)
│   │   ├── core/            # config, database session, security, observability
│   │   └── modules/         # modular monolith, one folder per PRD §5.2 module
│   │       ├── auth/        #   models, schemas, router, dependencies
│   │       ├── chat/        #   chat request flow
│   │       ├── conversations/
│   │       ├── regulations/
│   │       ├── ingestion/
│   │       ├── retrieval/
│   │       ├── generation/  #   LLM provider adapter
│   │       ├── feedback/
│   │       ├── evaluation/
│   │       └── audit/
│   ├── migrations/          # Alembic
│   └── tests/
├── frontend/                # React + TypeScript (Vite), feature-based folders
├── infra/postgres/init/     # SQL run when the Docker database is first created
├── docker-compose.yml       # PostgreSQL + pgvector for local development
├── Makefile                 # common commands (`make help`)
└── prd.md                   # product requirements
```

Each backend module owns its models, schemas, and routes. Request handlers get a database session through `app.core.database.SessionDep`: one transaction per request, committed before the response is sent and rolled back on any error.

## Requirements

- Python 3.10+, Node.js 20+ and npm
- A Docker runtime (Docker Desktop, OrbStack, or Colima) for PostgreSQL + pgvector
- An OpenAI API key for model-backed answers (optional for development; without it the chat reports that AI is not configured)

## Configure and run

```bash
make install                              # backend venv + frontend packages
cp backend/.env.example backend/.env      # then set AUTH_SECRET_KEY and ADMIN_TOKEN (openssl rand -hex 32)
make db-up                                # PostgreSQL + pgvector on localhost:5432 (creates taxora and taxora_test)
make migrate                              # apply Alembic migrations
make api                                  # http://localhost:8000  (docs at /docs)
make web                                  # http://localhost:5173  (separate terminal)
```

Open the Vite URL, then register an account or sign in. Sessions use an HTTP-only cookie; set `AUTH_COOKIE_SECURE=true` behind HTTPS.

`VITE_API_URL` in `frontend/.env.local` overrides the API origin (default `http://localhost:8000`). The backend's `FRONTEND_ORIGIN` must match the browser origin. In production, serve frontend and API under the same site (for example `app.example.com` and `api.example.com`) over HTTPS so the `SameSite=Lax` cookie is sent.

The API and frontend run natively for fast reloads and debugging; Docker is only used for the database. A production API image is not defined yet.

## Tests and checks

```bash
make test    # backend tests; database tests are skipped with a notice if `make db-up` has not been run
make lint    # ruff
```

Database tests run against the `taxora_test` database (override with `TEST_DATABASE_URL`), apply migrations once per run, and truncate tables after each test.

## Frontend commands

From `frontend/`: `npm run dev`, `npm run build` (type check + production build), `npm run preview`.

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

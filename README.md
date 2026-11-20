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
- An [OpenRouter](https://openrouter.ai/keys) API key in `LLM_API_KEY` for generated answers (free tier: 50 requests/day; optional for development, since without it the chat reports that AI is not configured). Any OpenAI-compatible API works via `LLM_BASE_URL` and `LLM_MODEL`.
- About 250 MB of disk for the local embedding model, downloaded automatically on first use

## Configure and run

```bash
make install                              # backend venv + frontend packages
cp backend/.env.example backend/.env      # then set AUTH_SECRET_KEY (openssl rand -hex 32)
make db-up                                # PostgreSQL + pgvector on localhost:5432 (creates taxora and taxora_test)
make migrate                              # apply Alembic migrations
make api                                  # http://localhost:8000  (docs at /docs)
make web                                  # http://localhost:5173  (separate terminal)
make seed                                 # dev accounts, password password123:
                                          #   admin@example.com, reviewer@example.com, user@example.com
```

To change the role of any other registered account: `make set-role EMAIL=you@example.com ROLE=admin`.

Open the Vite URL, then register an account or sign in. Sessions use an HTTP-only cookie; set `AUTH_COOKIE_SECURE=true` behind HTTPS.

`VITE_API_URL` in `frontend/.env.local` overrides the API origin (default `http://localhost:8000`). The backend's `FRONTEND_ORIGIN` must match the browser origin. In production, serve frontend and API under the same site (for example `app.example.com` and `api.example.com`) over HTTPS so the `SameSite=Lax` cookie is sent.

The API and frontend run natively for fast reloads and debugging; Docker is only used for the database. A production API image is not defined yet.

## AI and chat safety

- **Embeddings** (finding relevant articles) run locally with `fastembed` and the multilingual model `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions). No text leaves the server for search. Changing the model requires re-indexing every chunk.
- **LLM** (writing the answer) is called through an OpenAI-compatible API, OpenRouter's free router by default.
- Each question passes these layers, and each can stop it:
  1. **Scope guard** (`query_understanding`): a tax-term match, or embedding similarity to tax-topic anchors ≥ `SCOPE_MIN_SIMILARITY`. Off-topic questions get `answer_status: "out_of_scope"` without retrieval or an LLM call.
  2. **Relevance thresholds** in retrieval: keyword matches must match the query (OR of meaningful terms), vector matches must be within `RETRIEVAL_MAX_COSINE_DISTANCE`. No match means `insufficient_evidence` and no LLM call.
  3. **Structured prompt**: the question, case context, and evidence are wrapped in tags and treated as untrusted data; text cannot open or close those tags.
  4. **Citation validation**: a claim is kept only if it cites evidence that was retrieved and quotes it verbatim; sources show the verified passage. If the model declares a question out of scope, its text is discarded.
  5. **Per-user chat limit** (`CHAT_REQUESTS_PER_HOUR`) to protect the shared LLM quota.
- Thresholds are initial values (the scope threshold was checked on 16 sample questions; the retrieval threshold has not been calibrated because no documents are indexed yet). Re-tune them on the evaluation dataset. These layers reduce, but cannot eliminate, prompt-injection risk; the answer text itself is not checked claim by claim.
- Each answer stores its prompt version, model, scope decision, retrieved and cited evidence IDs, and latency in message metadata; prompts are not stored.

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
- Email/password registration and sign-in are implemented. Passwords are hashed with Argon2id; browser sessions use signed, HTTP-only cookies (API clients may send the same token as `Authorization: Bearer`). Login is limited to `AUTH_LOGIN_ATTEMPTS_PER_MINUTE` and registration to `AUTH_REGISTRATIONS_PER_HOUR` per client IP; the limiter is in-memory, so counts are per API process. Google OAuth, email verification, password reset, and session revocation are not implemented yet.
- Roles are `user` (default), `reviewer`, and `admin`. Grant one to a registered account with `make set-role EMAIL=you@example.com ROLE=admin`; the change is written to `audit_logs`, and it applies on the next request (reload the page to update the UI). There is no static admin token.
- `POST /api/v1/chat` accepts `response_language: "en" | "id"` (defaults to Indonesian for existing clients); the selected value is retained in message metadata.
- Conversation list/detail, published regulation listing, and administrator ingestion routes are connected to the backend. The UI does not invent regulations, sources, or successful answers.
- Backend conversation detail currently returns message content and metadata but not source records; therefore reloaded history cannot restore citation cards or per-message feedback state. A successful chat fetches its assistant message ID for feedback because the chat response returns a request ID rather than message ID.
- `LLM_API_KEY` is a server-side credential configured by the operator; users never supply provider keys. With OpenRouter, requests are restricted to zero-data-retention providers (`LLM_ZERO_DATA_RETENTION`), which can leave the free router with no eligible model; the chat then returns a `failed` status. Authentication currently uses first-party email/password accounts; use HTTPS, secure cookies, rate limiting, and a security review before public launch.
- Backend upload currently rejects document uploads after validation, and the ingestion endpoint processes synchronously. This frontend exposes URL ingestion only, matching the functional endpoint available now.
- Ingestion status is visible in the admin screen, but approval/publication actions, audit history, evaluation results, and regulation-version editing are not yet exposed in the frontend.
- The source library contains only published regulations returned by the backend; it does not seed sample legal data. No evaluation scores or verified legal coverage are claimed.
- The backend returns an unavailable evaluation status until a reviewed evaluation dataset exists. RAG quality, legal verification, production auth hardening, and broader PRD features remain incomplete.

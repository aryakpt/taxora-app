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

## Knowledge base ingestion

```text
queued ─▶ processing ─▶ review_required ─(reviewer)─▶ approved ─(admin)─▶ published
              └───────▶ failed ─(admin retry)─▶ queued
```

- **Admin UI** (`/admin` in the web app; reviewers and admins): admins add a document by official link or PDF upload, the job list refreshes itself while processing, and the review panel shows the extracted sections, the stored original for download, and the regulation dates. Reviewers can correct the dates while the document is under review (`PUT .../{id}/dates`; locked after approval) and approve only after confirming they compared it with the source; admins publish and retry.
- **Submit** (admin): `POST /api/v1/admin/ingestion` with an official PDF link, or `POST /api/v1/admin/ingestion/upload` (multipart: PDF plus the same metadata fields). Metadata (type, number, title, issuer, topic, dates) is entered by people, never inferred. The request returns `202` and processing continues in the background; poll `GET /api/v1/admin/ingestion/{id}`.
- **Sources**: links must be `https` on `INGESTION_ALLOWED_HOSTS` (default: peraturan.bpk.go.id, jdih.kemenkeu.go.id, pajak.go.id). Every redirect is re-checked and downloads are capped at `MAX_UPLOAD_BYTES`. Use the direct PDF link (on BPK: the `/Download/...pdf` link, not the `/Details/...` page).
- **Processing**: the original PDF is stored by SHA-256 under `DOCUMENT_STORAGE_DIR` (`backend/storage/documents`, git-ignored); text is extracted (page-number lines removed), split into preamble, one section per `Pasal` (including Roman-numbered amendment articles), and attachments (`LAMPIRAN`), chunked, and embedded locally.
- **Idempotent**: one regulation per type + number. Resubmitting an identical file reuses the existing version; a changed file becomes a new version of the same regulation.
- **Review**: `GET .../{id}/provisions` (extracted sections) and `GET .../{id}/document` (stored original, sent as a download) let the reviewer check the extraction. `POST .../{id}/approve` (reviewer or admin) after checking text and metadata against the source, then `POST .../{id}/publish` (admin). Only published versions are used by chat and the regulation library. `POST .../{id}/retry` re-runs a failed job without downloading the stored file again. Each step is written to `audit_logs`.
- **Limits**: scanned PDFs without a text layer fail (no OCR yet). pypdf occasionally splits a word (about 1 in 200 occurrences on PMK 28/2026). Jobs run inside the API process; a restart marks unfinished jobs failed (retryable). Paragraph (ayat) level structure and regulation relations are not extracted yet.
- **Retrieval tuning** (`RETRIEVAL_MAX_COSINE_DISTANCE=0.7`, `RETRIEVAL_KEYWORD_WEIGHT=0.1`): measured on 6 questions against PMK 28/2026, the expected article was in the top 5 for all 6 and an off-topic question returned nothing; with equal keyword weight, only 3 of 6. Re-tune on the evaluation dataset as documents are added.

## AI and chat safety

- **Embeddings** (finding relevant articles) run locally with `fastembed` and the multilingual model `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions). No text leaves the server for search. Changing the model requires re-indexing every chunk.
- **LLM** (writing the answer) is called through an OpenAI-compatible API, OpenRouter's free router by default.
- Each question passes these layers, and each can stop it:
  1. **Scope guard** (`query_understanding`): a tax-term match, or embedding similarity to tax-topic anchors ≥ `SCOPE_MIN_SIMILARITY`. Off-topic questions get `answer_status: "out_of_scope"` without retrieval or an LLM call.
  2. **Relevance thresholds** in retrieval: keyword matches must match the query (OR of meaningful terms), vector matches must be within `RETRIEVAL_MAX_COSINE_DISTANCE`. No match means `insufficient_evidence` and no LLM call.
  3. **Structured prompt**: the question, case context, and evidence are wrapped in tags and treated as untrusted data; text cannot open or close those tags.
  4. **Citation validation**: a claim is kept only if it cites evidence that was retrieved and quotes it verbatim; sources show the verified passage. If the model declares a question out of scope, its text is discarded.
  5. **Per-user chat limit** (`CHAT_REQUESTS_PER_HOUR`) to protect the shared LLM quota.
- **Follow-up questions**: the last 2 exchanges of a conversation are sent to the LLM inside `<history>` (untrusted, never evidence), and the previous question is added to the scope check and the search, so "lalu apa syaratnya?" keeps its meaning. Out-of-scope turns are never replayed.
- **LLM models**: `LLM_MODEL` is tried first and `LLM_FALLBACK_MODELS` after it. A retry (empty, cut-off, timed-out, or invalid reply, up to `LLM_ATTEMPTS`) starts at the next model, and on OpenRouter the rest of the list is sent as server-side fallbacks, so a rate-limited or withdrawn model is skipped immediately. Every free OpenRouter model is currently a reasoning model; measured on 2026-11-23, replies took 12-45 s and roughly a third of questions still failed after two attempts. Free models change often: when chat starts failing, check `make ask-raw` and https://openrouter.ai/models?max_price=0. A paid model (for example `anthropic/claude-haiku-5.5`, about $0.0014 per question) avoids this; set `LLM_REASONING_EFFORT=` (empty) for models that do not need it.
- **The question is the whole input**: there are no separate tax period or taxpayer fields. A tax year in the question ("tahun pajak 2024", "masa pajak Maret 2025") selects the rules in force at the end of that year; "PMK 28 Tahun 2026" is recognised as a regulation number, not a tax year. Missing facts are listed by the model in `missing_information`.
- Thresholds are initial values, calibrated on small samples (scope: 10 tax questions without tax terms vs 15 off-topic ones; retrieval: questions against one regulation). Re-tune them with `make eval` as documents are added. These layers reduce, but cannot eliminate, prompt-injection risk; the answer text itself is not checked claim by claim.
- Each answer stores its prompt version, the model that actually answered (a router picks one per request), failed attempts, scope decision, history length, retrieved and cited evidence IDs, and latency in message metadata; prompts are not stored.

## Evaluation and baseline

- `make eval` scores the scope guard and retrieval on `backend/app/modules/evaluation/cases/pmk_28_2026.json` (no LLM call, free and repeatable); `make eval-draft` also searches documents still under review. Results are stored in `evaluation_runs` and listed at `GET /api/v1/admin/evaluations`.
- The dataset's expected articles were labeled from the extracted text and have **not been confirmed by a tax reviewer** (`reviewed_by: null`); treat scores as indicative. Current result on PMK 28/2026: expected article in the top 5 for 10 of 14 questions, all 6 off-topic questions refused.
- `make ask-raw Q="..."` asks the configured LLM directly, without sources, scope guard, or citation checks, to compare a plain LLM answer with Taxora's.
- `make reprocess JOB=<id>` re-extracts a document that is still under review with the current extractor. Approved and published versions are never changed.

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
- `LLM_API_KEY` is a server-side credential configured by the operator; users never supply provider keys. `LLM_DATA_POLICY` controls which OpenRouter providers may receive prompts: `no_training` (default; providers may not train on or sell prompts but may retain them for a time), `zero_retention` (no retention at all; as of November 2026 no free model qualifies, so it needs a paid model), or `any`. Review this before handling real user data. If no provider matches the policy, the chat returns a `failed` status. Authentication currently uses first-party email/password accounts; use HTTPS, secure cookies, rate limiting, and a security review before public launch.
- The frontend exposes URL ingestion only; PDF upload (`POST /api/v1/admin/ingestion/upload`) is available in the API.
- Ingestion status is visible in the admin screen, but approve/publish/retry, audit history, evaluation results, and regulation-version editing are not yet exposed in the frontend; use the API (`/docs`).
- The source library contains only published regulations returned by the backend; it does not seed sample legal data. No evaluation scores or verified legal coverage are claimed.
- The backend returns an unavailable evaluation status until a reviewed evaluation dataset exists. RAG quality, legal verification, production auth hardening, and broader PRD features remain incomplete.

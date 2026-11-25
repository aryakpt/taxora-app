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

## Sign in with Google

Optional. Without `GOOGLE_CLIENT_ID` the login page shows only email and password.

1. Google Cloud Console → APIs & Services → **OAuth consent screen**: set it up (External, app name, support email).
2. **Credentials → Create credentials → OAuth client ID**, type **Web application**. Under *Authorized JavaScript origins* add `http://localhost:5173` (and the production URL later). No redirect URI is needed.
3. Put the client ID in `backend/.env` as `GOOGLE_CLIENT_ID=...apps.googleusercontent.com` and restart the API. No client secret is used; the frontend reads the ID from `GET /api/v1/auth/providers`.

The backend verifies Google's signature, the audience (this client ID), the issuer, the expiry, and that Google has verified the email. The first sign-in creates an account with role `user`, or links an existing account with the same email. Google-only accounts have no password.

## Knowledge base ingestion

```text
queued ─▶ processing ─▶ review_required ─(reviewer)─▶ approved ─(admin)─▶ published
              └───────▶ failed ─(admin retry)─▶ queued
```

- **Admin UI** (reviewers and admins): `/admin` is the document table (search by type, number, title or file; filter by status with counts; paginated, 10/20/50 rows; the view lives in the URL); `GET /api/v1/admin/ingestion?page=&page_size=&status=&q=` returns `{items, total, page, page_size, status_counts}`. `/admin/documents/new` (admins) adds a document by official link or PDF upload: the type is shown with its full name and fills in the issuing authority, and every field has an explanation ("?"). `/admin/documents/{id}` shows one document: extracted sections, the stored original, the regulation dates, and the review actions; it refreshes itself while processing. Reviewers can correct the dates while the document is under review (`PUT .../{id}/dates`; locked after approval) and approve only after confirming they compared it with the source; admins publish and retry.
- **Submit** (admin): `POST /api/v1/admin/ingestion` with an official PDF link, or `POST /api/v1/admin/ingestion/upload` (multipart: PDF plus the same metadata fields). Metadata (type, number, title, issuer, topic, dates) is entered by people, never inferred. The request returns `202` and processing continues in the background; poll `GET /api/v1/admin/ingestion/{id}`.
- **Sources**: links must be `https` on `INGESTION_ALLOWED_HOSTS` (default: peraturan.bpk.go.id, jdih.kemenkeu.go.id, pajak.go.id). Every redirect is re-checked and downloads are capped at `MAX_UPLOAD_BYTES`. Use the direct PDF link (on BPK: the `/Download/...pdf` link, not the `/Details/...` page).
- **Processing**: the original PDF is stored by SHA-256 under `DOCUMENT_STORAGE_DIR` (`backend/storage/documents`, git-ignored); text is extracted (page-number lines removed), split into preamble, one section per `Pasal` (including Roman-numbered amendment articles), attachments (`LAMPIRAN`, before or after the elucidation), and the elucidation (`PENJELASAN`: the general part and one section per explained article, cited as "Penjelasan Pasal N", never as the article itself), chunked, and embedded locally.
- **Idempotent**: one regulation per type + number. Resubmitting an identical file reuses the existing version; a changed file becomes a new version of the same regulation.
- **Review**: `GET .../{id}/provisions` (extracted sections) and `GET .../{id}/document` (stored original, sent as a download) let the reviewer check the extraction. `POST .../{id}/approve` (reviewer or admin) after checking text and metadata against the source, then `POST .../{id}/publish` (admin). Only published versions are used by chat and the regulation library. `POST .../{id}/retry` re-runs a failed job without downloading the stored file again. Each step is written to `audit_logs`.
- **Reject and delete**: a reviewer can reject a document under review with a reason (`POST .../{id}/reject`); it is never searched, the reason shows in the review panel and the audit log, and submitting the same file again extracts it afresh for a new review. An admin can delete a document in any status except while it is processing (`DELETE .../{id}`): its version, provisions, chunks, every job of that version, the regulation if no other version is left, and the stored PDF if nothing else uses it. Deleting a published document stops chat citing it immediately; answers already given keep their stored sources.
- **Official link**: required when submitting by link (the PDF is downloaded from it), optional for uploads. Without it, sources and the regulation library show no link.
- **Edit** (admin): `PUT /api/v1/admin/ingestion/{id}` (page `/admin/documents/{id}/edit`) changes the type, number, title, issuer, topic, or dates, with a required reason; the file and its official link cannot be changed (submit a new document). An approved, published, or rejected document goes back to review, so a published one leaves the assistant until it is approved and published again. A new type or number moves the document to that regulation (found or created; refused when that regulation already has the same file) and removes the old regulation when nothing uses it. Old and new values are kept in `audit_logs.details` and shown as change history. Chunks hold only the legal text, so nothing is re-embedded.
- **Limits**: scanned PDFs without a text layer fail (no OCR yet). pypdf occasionally splits a word (about 1 in 200 occurrences on PMK 28/2026). Jobs run inside the API process; a restart marks unfinished jobs failed (retryable). Paragraph (ayat) level structure and regulation relations are not extracted yet. In omnibus amendments such as UU 7/2021 (HPP), the amended articles of several laws share numbers ("Pasal 4" of the KUP law and of the PPh law); citations show the number without saying which law it amends. Scanned PDFs with a poor OCR layer (for example PP 58/2023) extract with misread digits (`Rp5.4O0.OOO`).
- **Retrieval tuning** (`RETRIEVAL_MAX_COSINE_DISTANCE=0.7`, `RETRIEVAL_KEYWORD_WEIGHT=0.1`): measured on 6 questions against PMK 28/2026, the expected article was in the top 5 for all 6 and an off-topic question returned nothing; with equal keyword weight, only 3 of 6. Re-tune on the evaluation dataset as documents are added.

## AI and chat safety

- **Embeddings** (finding relevant articles) come from the Gemini API (`gemini-embedding-001`, 768 dimensions) through its OpenAI-compatible endpoint. The backend no longer loads a local model (about 250 MB less memory, so it fits 512 MB free hosting). Requests are batched and paced under `EMBEDDING_TOKENS_PER_MINUTE` (free tier: 30,000 tokens per minute per model), and a rate limit waits for the delay Google asks for. Indexing a large regulation therefore takes minutes on the free tier. If embeddings fail, chat answers `failed` and ingestion jobs fail with a retryable message; without any key, only tax terms pass the scope guard and search uses keywords only. Changing the model or dimensions: migrate if the dimensions change, then `make reindex` (embeds every chunk without a vector; rerun it to continue after a quota stop).
- **LLM** (writing the answer) is called through an OpenAI-compatible API, OpenRouter's free router by default.
- Each question passes these layers, and each can stop it:
  1. **Scope guard** (`query_understanding`): a tax-term match, or embedding similarity to tax-topic anchors ≥ `SCOPE_MIN_SIMILARITY`. Off-topic questions get `answer_status: "out_of_scope"` without retrieval or an LLM call.
  2. **Relevance thresholds** in retrieval: keyword matches must match the query (OR of meaningful terms), vector matches must be within `RETRIEVAL_MAX_COSINE_DISTANCE`. No match means `insufficient_evidence` and no LLM call.
  3. **Structured prompt**: the question, case context, and evidence are wrapped in tags and treated as untrusted data; text cannot open or close those tags.
  4. **Citation validation**: a claim is kept only if it cites evidence that was retrieved and quotes it verbatim; sources show the verified passage. If the model declares a question out of scope, its text is discarded.
  5. **Per-user chat limit** (`CHAT_REQUESTS_PER_HOUR`) to protect the shared LLM quota.
- **Conversation groups**: users create their own groups (`/api/v1/conversation-groups`) and move a conversation in or out with `PATCH /api/v1/conversations/{id}` (`{"group_id": ...}` or `null`); in the sidebar via a conversation's menu or by dragging it onto a group. Group names are unique per user. Deleting a group keeps its conversations, ungrouped. Moving or renaming does not change the history order.
- **Follow-up questions**: the last 2 in-scope exchanges of a conversation are sent to the LLM inside `<history>` (untrusted, never evidence), with what each answer asked the user to clarify; out-of-scope turns are skipped (never replayed) and do not use up the window. In a conversation that already has an in-scope turn, a follow-up skips the embedding scope guard ("belum kawin, gaji tetap" answers Taxora's own question) and the LLM judges it instead (`in_scope: false` → out of scope). Retrieval searches the earlier questions, the requested clarifications, and the new message together.
- **LLM models**: `LLM_MODEL` is tried first and `LLM_FALLBACK_MODELS` after it. A retry (empty, cut-off, timed-out, or invalid reply, up to `LLM_ATTEMPTS`) starts at the next model, and on OpenRouter the rest of the list is sent as server-side fallbacks, so a rate-limited or withdrawn model is skipped immediately. Every free OpenRouter model is currently a reasoning model; measured on 2026-11-23, replies took 12-45 s and roughly a third of questions still failed after two attempts. Free models change often: when chat starts failing, check `make ask-raw` and https://openrouter.ai/models?max_price=0. A paid model (for example `anthropic/claude-haiku-5.5`, about $0.0014 per question) avoids this; set `LLM_REASONING_EFFORT=` (empty) for models that do not need it.
- **Quota**: OpenRouter's free tier allows 50 free-model requests a day (1000 after buying $10 of credits; check with `GET https://openrouter.ai/api/v1/key`). When the daily quota is used up, the chat answers `failed` with the reset time in WIB, does not retry, and stops calling the provider until the reset. Every LLM attempt counts, including retries, `make ask-raw`, and live testing.
- **General answers** (`CHAT_ALLOW_GENERAL_ANSWERS=true`, default): only the *topic* is restricted. A tax question the knowledge base cannot answer still gets an answer from the model's general knowledge, with status `general_answer`, a "not verified against regulations" label, no sources, and a warning that rates and deadlines may have changed. Statements backed by a quoted regulation are `answered` with sources as before. Off-topic questions are refused in both modes. Set it to `false` for the strict, evidence-only behaviour.
- **Answer language** follows the question (Indonesian or English, by counting common words; tax terms are ignored), including Taxora's fixed messages. The interface language decides only when the question gives no signal ("halo", "PPh 21?"). Interface labels stay in the interface language.
- **Answer formatting**: the model writes answers in Markdown (lists, bold, tables); the frontend renders them with `react-markdown` + GFM, loaded on demand. Raw HTML is never rendered, links from the model are shown as plain text (verified links live only in the source cards), and images are dropped. The user's own messages stay plain text.
- **The question is the whole input**: there are no separate tax period or taxpayer fields. A tax year in the question ("tahun pajak 2024", "masa pajak Maret 2025") selects the rules in force at the end of that year; "PMK 28 Tahun 2026" is recognised as a regulation number, not a tax year. Missing facts are listed by the model in `missing_information`.
- Thresholds are initial values, calibrated on small samples (scope: 10 tax questions without tax terms vs 15 off-topic ones; retrieval: questions against one regulation). Re-tune them with `make eval` as documents are added. These layers reduce, but cannot eliminate, prompt-injection risk; the answer text itself is not checked claim by claim.
- Each answer stores its prompt version, the model that actually answered (a router picks one per request), failed attempts, scope decision, history length, retrieved and cited evidence IDs, and latency in message metadata; prompts are not stored.

## Evaluation and baseline

- `make eval` scores the scope guard and retrieval on every dataset in `backend/app/modules/evaluation/cases/` (no LLM call, free and repeatable); `make eval-draft` also searches documents still under review. Results are stored in `evaluation_runs` and listed at `GET /api/v1/admin/evaluations`. A case can list `alternatives`, for example the amending regulation that rewrote the expected article.
- The datasets' expected articles were located in the extracted text and have **not been confirmed by a tax reviewer** (`reviewed_by: null`); treat scores as indicative. With the eight core PPh/PPN regulations added (Nov 2026, draft search): expected article in the top 5 for 6 of 14 core questions and 8 of 14 PMK 28/2026 questions (10 of 14 when PMK 28/2026 was the only document). Retrieval quality drops as the knowledge base grows; improving it is the next step.
- `make ask-raw Q="..."` asks the configured LLM directly, without sources, scope guard, or citation checks, to compare a plain LLM answer with Taxora's.
- `make reprocess JOB=<id>` re-extracts a document that is still under review with the current extractor. Approved and published versions are never changed.

## Deployment

Free tier, no payment card: one **Vercel** project serves the frontend and the API (Vercel Services, `vercel.json`: `/api/*` → FastAPI in `backend/`, everything else → the Vite build in `frontend/`, region Tokyo), with **Supabase** for PostgreSQL + pgvector and Storage for the original PDFs. Frontend and API share one origin, so the session cookie is first-party and no CORS is involved.

Secrets live only in `deploy/.env.production` (git-ignored; template `deploy/env.production.example`) and in Vercel's environment variables. The `make` commands below read that file and print only variable names; `.vercelignore` keeps `deploy/` and every `.env` out of uploads.

1. **Supabase**: create a project (Data API off). Fill `SUPABASE_URL`, a **secret** API key (`sb_secret_…`, not the publishable one), the *Session pooler* connection string and the database password. The direct connection (`db.<ref>.supabase.co`) is IPv6-only; use the pooler.
2. **Database**: `make prod-migrate`, then `make prod CMD=prepare-storage` (creates the private `documents` bucket). Run `make prod-migrate` again whenever a release adds a migration.
3. **Knowledge**: `make prod CMD=copy-knowledge` copies published regulations with their embeddings and PDFs from the local database (no embedding quota spent; existing rows are skipped). Chunks the local database never embedded are copied without a vector: then `make prod CMD=reindex`.
4. **Deploy**: `make deploy-env` links the repository to the Vercel project `VERCEL_PROJECT` and sets the production variables (a session signing key is generated once and kept in the file); `make deploy` builds and deploys both services; `make deploy-logs` shows runtime logs. Connect the repository in the Vercel dashboard (Project → Settings → Git) to deploy every merge to `main`.
5. **Accounts**: register on the site, then `make prod CMD="set-role you@example.com admin"`. For Google sign-in, add the site's URL to the OAuth client's *Authorized JavaScript origins*.

Serverless limits (Hobby): a request runs at most 300 s, so documents are processed inside the upload request (`INGESTION_INLINE`), and request bodies are capped at 4.5 MB (`MAX_UPLOAD_BYTES` is 4 MB): submit larger documents by their official link, or ingest them locally and `copy-knowledge`. Supabase pauses a project after a week without activity; the Gemini free tier allows about 1,000 embedding requests a day per Google Cloud project (one per chat question, one per chunk when ingesting).

## Tests and checks

```bash
make test    # backend tests; database tests are skipped with a notice if `make db-up` has not been run
make lint    # ruff
```

Database tests run against the `taxora_test` database (override with `TEST_DATABASE_URL`), apply migrations once per run, and truncate tables after each test.

### Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`:

- **Backend**: `ruff check`, then `pytest` against PostgreSQL + pgvector (the same `pgvector/pgvector:pg16` image, with the test database created by `infra/postgres/init/01-databases.sql`). `REQUIRE_TEST_DATABASE=1` makes database tests fail instead of being skipped if the database is unreachable, so a broken setup cannot pass as green.
- **Frontend**: `npm ci` and `npm run build` (TypeScript type check + production build).

Run the same checks locally with `make check` (needs `make db-up`).

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
- The source library contains only published regulations returned by the backend; it does not seed sample legal data. No evaluation scores or verified legal coverage are claimed.
- The backend returns an unavailable evaluation status until a reviewed evaluation dataset exists. RAG quality, legal verification, production auth hardening, and broader PRD features remain incomplete.

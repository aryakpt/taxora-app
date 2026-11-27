# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Taxora is an evidence-first assistant for questions about Indonesian tax (PPh, PPN). The backend is FastAPI with async SQLAlchemy on PostgreSQL + pgvector. The frontend is React 18 + TypeScript (Vite, SCSS, i18next). `prd.md` is the product spec. `README.md` is detailed and up to date on behaviour (ingestion lifecycle, the chat safety layers, thresholds, deployment), so read the relevant section before changing one of those areas.

## Commands

All of these run from the repo root (`make help` lists them). Only Docker runs the database. The API and the web app run natively.

```bash
make install            # backend/.venv + frontend npm ci
make db-up              # Postgres+pgvector on 127.0.0.1:5432 (creates taxora and taxora_test)
make migrate            # alembic upgrade head
make api                # uvicorn --reload on :8000 (docs at /docs)
make web                # Vite on :5173
make seed               # admin/reviewer/user@example.com, password password123
make test               # pytest; DB tests are skipped if the database is down
make lint               # ruff check app tests
make check              # what CI runs: ruff, pytest with REQUIRE_TEST_DATABASE=1, frontend build
```

Running a single test (from `backend/`):

```bash
.venv/bin/pytest tests/test_chat.py::test_name -q
.venv/bin/pytest -k "ingestion and not units"
```

Frontend (from `frontend/`): `npm run build` runs `tsc -b` and then the Vite build. It is the only type check, and the frontend has no tests and no linter.

Domain CLI (`backend/app/cli.py`, wrapped by make): `eval` / `eval-draft` (score the scope guard and retrieval on `modules/evaluation/cases/`, no LLM call), `ask-raw Q=...` (plain LLM baseline; it **uses up the OpenRouter free daily quota**), `reindex` (embed chunks that have no vector), `reprocess JOB=<id>`, `set-role EMAIL= ROLE=`.

Migrations live in `backend/migrations/versions/` and are numbered `NNNN_name.py`. Add new ones with the next number, by hand or with `alembic revision --autogenerate` run from `backend/`. Every model module must be imported in `app/models.py`, or Alembic and the test truncation will not see it.

## Production boundary

Nothing in this repo connects to production (Vercel + Supabase), and nothing should. Do not add deploy scripts, production `make` targets, or commands that reach the production database or storage. Production changes go through the dashboards. For schema changes, `make migration-sql FROM=<revision>` prints offline SQL that the user runs in the Supabase SQL Editor. `vercel.json` routes `/api/*` to the FastAPI service in `backend/` and everything else to the Vite build, on one origin. When `APP_ENV=production`, `Settings` refuses unsafe config: insecure cookies, the dev database password, or missing Supabase storage keys.

## Backend architecture

It is a modular monolith. `app/modules/<name>/` each owns its `models.py`, `schemas.py`, `router.py`, and `service.py`. `app/main.py` registers every router under `/api/v1`. When the app starts, it marks interrupted ingestion jobs as failed.

- **Sessions**: always inject `app.core.database.SessionDep`, never a bare `Depends(get_session)`. The dependency is scoped to the function and gives one transaction per request: it commits before the response is sent and rolls back on any error. Mixing the two forms opens two sessions. Services call `flush()` and leave the commit to the dependency.
- **Auth** (`modules/auth`): Argon2id passwords, a signed HTTP-only session cookie (a Bearer header also works), and optional Google ID-token sign-in. Roles are `user`, `reviewer`, and `admin`, enforced with the `AdminUser` and `ReviewerUser` annotated dependencies from `auth/dependencies.py` (built on `require_role`). Session tokens carry `users.session_version`, and raising it (logout, linking Google to a password account) ends every session of that account. Rate limits (`core/rate_limit.py`) are counted in the PostgreSQL table `rate_limit_hits`, in their own transaction, so every instance shares them and a failed request still counts.
- **Chat pipeline** (`modules/chat/service.py::answer_question`). Any step below can end the request early with a status (`out_of_scope`, `insufficient_evidence`, `failed`, `general_answer`, `answered`):
  1. `query_understanding`: language detection (`language.py`, from the question text, with the UI language only breaking ties), the tax year in force (`period.py`), and the scope guard (`scope.py`: tax terms, or embedding similarity to anchor phrases).
  2. `retrieval/service.py`: hybrid search that merges keyword matches and pgvector cosine-distance matches (each under its own threshold) with Reciprocal Rank Fusion. It only searches versions in force on the reference date. Chat searches only `published` versions, and the `statuses` parameter is there only for offline evaluation.
  3. `generation`: `prompts.py` (a versioned prompt that wraps untrusted input in tags), `llm.py` (an OpenAI-compatible client with a model fallback list, retries, and quota handling), and `embeddings.py` (Gemini through its OpenAI-compatible endpoint, paced by tokens per minute).
  4. `chat/citations.py`: a claim is kept only if it quotes retrieved evidence verbatim.
  The assistant message stores a full trace in `metadata_json`, including a `display` block, so a reopened conversation renders the same sources.
- **AI providers** are reached only through `generation/providers.get_embedder()` and `get_llm()`, which return `None` when no API key is set, and callers must handle that. Tests monkeypatch these two functions.
- **Ingestion** (`modules/ingestion`) follows `queued → processing → review_required → approved → published`, with branches to `failed` (retryable) and rejected. `sources.py` checks the https link against an allowlist and re-checks every redirect. `storage.py` stores originals by SHA-256, on local disk or in Supabase Storage. `extraction.py` uses pypdf and splits the text into preamble, `Pasal`, `LAMPIRAN`, and `PENJELASAN` sections. `service.py` handles the state transitions, editing, and deletion, and every step writes to `audit_logs`. Jobs run as background tasks inside the API process, or inside the request when `INGESTION_INLINE` is set, because Vercel caps a request at 300 s. Regulation metadata is always entered by people and never inferred.
- **Data model** (`modules/regulations/models.py`): `Regulation` (unique on type + number) → `RegulationVersion` (one per distinct file) → `LegalProvision` (sections) → `DocumentChunk` (text plus `vector(768)`). If `EMBEDDING_DIMENSIONS` changes, a migration and `make reindex` are needed.

## Tests

`tests/conftest.py` sets environment variables before importing `app`, because settings and the engine are created at import time. Tests use the `taxora_test` database or `TEST_DATABASE_URL`, and run Alembic once per session.

- Mark database tests with `pytest.mark.db`, usually as a module-level `pytestmark`. The mark pulls in `clean_database`, which truncates every table after each test.
- The autouse fixture `fake_ai` replaces the embedder and LLM with `tests/fakes.py`. The LLM is off by default, and a test turns it on with `fake_ai.enable_llm(response)`, where the response can be a string, an exception, or a list for successive attempts. Tests never call a real provider.
- Rate-limit counts live in the database, so the table truncation resets them. An autouse fixture points document storage at a temporary path (Supabase is disabled).
- Use the `client` fixture (an httpx client on an ASGI transport) for API tests. `tests/pdf_fixture.py` builds PDFs for the ingestion tests.

Ruff settings: line length 120, target py310, rules `E,F,I,B,UP`. B008 is ignored for FastAPI `Depends`/`File`.

## Frontend architecture

- `src/features/<feature>/{api,components,hooks,pages}`: `tax-assistant` (chat and conversations), `knowledge-admin` (the `/admin` document table, new, detail, and edit pages), and `regulation-library`. Code shared across features lives in `src/shared/`: the API client, auth, components, i18n, styles, and types.
- `src/App.tsx` owns the layout and the chat and conversation state (`useChat`, `useConversations`). Routes are in `src/router/AppRouter.tsx`.
- `shared/api/client.ts` is a single axios client with `withCredentials`. The base URL is `VITE_API_URL`, falling back to `http://localhost:8000` in dev and same-origin in production. FastAPI errors are normalised into `ApiError`.
- The UI is in English and Indonesian (`shared/i18n/resources.ts`), and every user-facing string goes there. The UI language is sent as `response_language`.
- Assistant answers render as Markdown through `react-markdown` + `remark-gfm`, loaded on demand. Raw HTML is never rendered, links from the model show as plain text, and images are dropped. User messages stay plain text.
- Styles are SCSS under `shared/styles/` (abstracts, base, components, layout, themes).

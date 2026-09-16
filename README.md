# Customer Support AI

Portfolio-grade customer support assistant built with Python, FastAPI, RAG, escalation logic, and evaluation workflows.

## Goal

Build a realistic AI support system that can:

- Answer customer questions using a knowledge base.
- Cite retrieved sources.
- Escalate risky or low-confidence conversations to a human ticket queue.
- Store conversations and feedback.
- Provide admin analytics.
- Run automated tests and AI evaluation checks.

## Planned Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL + pgvector in production
- SQLite for local development
- OpenAI API for generation and embeddings
- pytest + Ruff
- Custom offline and live evaluation workflows for RAG quality checks

## Quick Start

```bash
uv sync
cp .env.example .env
uv run python scripts/migrate_database.py
uv run uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Admin ticket workspace:

```text
http://127.0.0.1:8000/admin
```

## Evaluation

Run the offline quality checks:

```bash
uv run --locked python scripts/run_evaluation.py --report reports/evaluation.json
```

The offline suite covers 27 scenarios across all five knowledge-base topics,
including ambiguous questions, escalation, and conversation continuation. It
reports retrieval, citation, grounding, refusal, and escalation results separately.
JSON reports include per-example diagnostics. Exit codes are 0 for pass, 1 for
quality failures, and 2 for invalid inputs or output errors.

GitHub Actions runs tests, Ruff, and evaluations on Python 3.12 and 3.14 for pushes
and pull requests, without API credentials, and uploads evaluation reports.
See [Phase 7](docs/PHASE_7_QUALITY_AND_READINESS.md) for details and limitations.

The evaluation dataset lives in:

```text
data/evaluation/support_eval.jsonl
```

## Docker

Run the portfolio demo as a single FastAPI service:

```bash
docker compose up --build
```

## Project Status

Step 1 is project setup. The initial app exposes health and metadata endpoints while the RAG, database, chat, and evaluation layers are added step by step.

Step 2 adds a searchable local knowledge base with sample support documents, chunking, local keyword-vector retrieval, and source citations.

Step 3 adds a grounded chat API, local conversation/message storage, refusal behavior for weak context, and user feedback capture.

Step 4 adds deterministic escalation rules, automatic ticket creation, and admin ticket endpoints.

Step 5 adds offline evaluation checks for retrieval, citations, refusal behavior, and escalation correctness.

Step 6 adds a same-origin chat UI, admin ticket dashboard, Docker setup, and architecture documentation.

Step 7 adds access controls, optional semantic retrieval and AI generation, expanded offline evaluation, and automated CI. Live-model calibration and production deployment remain outstanding.

## Current Endpoints

```text
GET /health
GET /
GET /admin
GET /knowledge/search?q=refund
POST /chat
POST /feedback
GET /admin/tickets
GET /admin/tickets/{ticket_id}
PATCH /admin/tickets/{ticket_id}
```

Read the phase explanations here:

```text
docs/PHASE_1_FOUNDATION.md
docs/PHASE_2_KNOWLEDGE_BASE.md
docs/PHASE_3_CHAT_API.md
docs/PHASE_4_ESCALATION_AND_TICKETS.md
docs/PHASE_5_EVALUATION.md
docs/PHASE_6_PORTFOLIO_POLISH.md
docs/PHASE_7_QUALITY_AND_READINESS.md
docs/ARCHITECTURE.md
```

## Access Controls

Set `ADMIN_USERNAME` and a strong `ADMIN_PASSWORD` in `.env` to enable the
admin workspace and ticket API. Admin access is disabled when the password is
empty. The browser prompts for these credentials at `/admin`; API clients can
use HTTP Basic authentication. Use HTTPS for any hosted deployment.

A new `POST /chat` response includes a `conversation_token`. Clients must send
that token with the conversation ID when continuing a chat or submitting
feedback. The chat UI keeps it in memory for the current page session. Only a
hash is stored in the database. Existing conversations created before this
change have no token and cannot be resumed; start a new conversation instead.
Use the migration script to create or upgrade database tables. Existing
unversioned databases require a backup and `--adopt-legacy`; see the storage guide.

Feedback message IDs must belong to the authorized conversation and identify an
assistant response. Tests use isolated in-memory databases.

The default offline engine uses keyword retrieval and document excerpts. Set
`AI_MODE=openai` to use semantic retrieval and model-generated answers as described below.


## AI Mode

The app defaults to `AI_MODE=offline` and makes no OpenAI requests in that mode.
To enable semantic retrieval and grounded generation, set these in `.env`:

```dotenv
AI_MODE=openai
OPENAI_API_KEY=your-key-here
OPENAI_CHAT_MODEL=gpt-5.4-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Restart the server after changing settings. OpenAI mode requires a nonempty API
key at startup. Both model names are configurable; account access and billing are
required. The key stays on the backend. Do not commit `.env`.

In OpenAI mode, the backend embeds knowledge-base chunks in batches and caches
the index in memory per worker. Editing document contents rebuilds the index on
the next request; restarting a worker also requires embedding the documents again.
Customer queries are embedded per request and are not cached. The default vector store searches locally. `VECTOR_STORE=pgvector` enables
persistent PostgreSQL search with explicit indexing; see the storage guide.

Generation uses the Responses API with structured output and `store=False`.
Only the current question, retrieved document text, and up to six recent messages
from that conversation are sent for generation. Conversation tokens, admin
credentials, and database IDs are not included. User-provided text can still
contain personal data; this is not a PII-redaction system.

The server accepts only citations matching retrieved chunk IDs, and renders the
citation labels itself. Empty answers, unknown citations, model refusals,
incomplete responses, and provider errors trigger human escalation. Billing and
account escalation rules still apply to successful generated answers. Citation
validation does not prove every generated claim is supported; live quality
assessment is still required.

`SEMANTIC_MIN_SCORE=0.35` and `SEMANTIC_HIGH_SCORE=0.65` are initial heuristic
thresholds, not calibrated probabilities. Tune them with real examples before
production. `OPENAI_TIMEOUT_SECONDS=20` bounds each provider request, with automatic
retries disabled. `HISTORY_MESSAGE_LIMIT=6` bounds history messages (0 disables
history). Short follow-ups containing pronouns also include the previous customer
question in their retrieval query.

Run `uv run pytest -q` for offline regression tests, including mocked OpenAI HTTP
responses and generation validation cases in
`data/evaluation/generation_cases.jsonl`. The evaluation CLI always uses the
offline engine, even when OpenAI mode is configured, and does not measure live
model quality or spend API credits.

Implementation references: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
and [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings).

## Live Quality Evaluation

A separate command runs real OpenAI requests with the existing chat service:

```bash
uv run --locked python scripts/run_live_evaluation.py --limit 2 --max-calls 10 --report reports/live-smoke.json
```

It requires `OPENAI_API_KEY` in `.env` and uses API credits. The app can remain
in offline mode. The full suite contains 18 cases, split into calibration and
held-out validation. Reports include actual scores, responses, model-grader
assessments, usage, and candidate retrieval cutoffs. Thresholds are never changed
automatically; automated grades require human review. No live run has yet been
completed during development.

See [Live AI evaluation](docs/LIVE_AI_EVALUATION.md) for full-run commands,
report interpretation, request limits, and calibration limitations. Offline CI
and the existing evaluator do not initiate live requests.

## Production Storage

Versioned migrations and PostgreSQL/pgvector storage are implemented. Read
[Production storage](docs/PRODUCTION_STORAGE.md) for legacy SQLite adoption,
PostgreSQL Compose setup, persistent indexing, and integration tests. The app no
longer creates tables during requests; run migrations before starting it.

Desktop chat/admin flows and the Docker image have been verified locally against
PostgreSQL in offline mode. See [Verification notes](docs/VERIFICATION.md) for the
checks and their limits. Live-model evaluation remains deferred.

## BeanCO Integration

This service can power the BeanCO storefront with a separate, store-specific knowledge pack. Run it locally on port 8001 while BeanCO's Django API uses port 8000:

```bash
KNOWLEDGE_BASE_DIR=data/knowledge_beanco uv run uvicorn app.main:app --port 8001
```

Run the matching offline quality suite with:

```bash
uv run --locked python scripts/run_evaluation.py --dataset data/evaluation/beanco_eval.jsonl --knowledge-base data/knowledge_beanco --report reports/beanco-evaluation.json
```

See [BeanCO storefront integration](docs/BEANCO_INTEGRATION.md) for the trust boundary, BeanCO configuration, and production notes.

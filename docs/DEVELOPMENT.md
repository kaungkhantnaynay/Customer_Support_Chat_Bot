# Development Guide

## Environment

Use Python 3.12+ and `uv`. Install runtime and development dependencies from the
lockfile:

```bash
uv sync --locked --group dev
cp .env.example .env
```

The optional `eval` dependency group contains Ragas for future work. It is not
needed for the custom offline evaluator or CI.

## Run The API

```bash
uv run --locked python scripts/migrate_database.py
uv run --locked uvicorn app.main:app --reload
```

- Chat: `http://127.0.0.1:8000/`
- API documentation: `http://127.0.0.1:8000/docs`
- Admin workspace: `http://127.0.0.1:8000/admin`

Set `ADMIN_PASSWORD` in `.env` to enable admin access. Offline mode is the default;
see the README for optional OpenAI mode and conversation access tokens.

## Quality Checks

Run from the repository root:

```bash
uv run --locked ruff check .
uv run --locked pytest -q
uv run --locked python scripts/run_evaluation.py --report reports/evaluation.json
```

Tests cover API contracts, access controls, retrieval, feedback, tickets, mocked
OpenAI integration, and evaluator correctness. API tests use in-memory databases.
No live API key is needed. Mocked provider responses exercise SDK integration;
they do not establish live answer quality.

The evaluator always uses the offline engine, even when `.env` selects OpenAI
mode. It covers 27 scenarios and outputs retrieval, citation, grounding, refusal,
escalation, and conversation-continuity results. Exit codes are 0 (pass), 1
(quality failure), and 2 (input/output error).

To inspect available evaluator options:

```bash
uv run --locked python scripts/run_evaluation.py --help
```

Add synthetic examples to `data/evaluation/support_eval.jsonl` before changing
retrieval behavior. Add generation examples and tests before substantial prompt
changes. Check expected facts against the Markdown knowledge base; do not weaken
expectations merely to make a failing run pass.

GitHub Actions runs the same checks on Python 3.12 and 3.14 and retains evaluation
reports. See [Phase 7](PHASE_7_QUALITY_AND_READINESS.md) for report fields, coverage,
and operational limitations.

## Optional Live Evaluation

The separate `scripts/run_live_evaluation.py` command requires an API key and
uses API credits. It is never run by CI. See [Live AI evaluation](LIVE_AI_EVALUATION.md)
for the smoke check, full suite, reporting, and threshold review procedure.

## Database Changes

See [Production storage](PRODUCTION_STORAGE.md) for schema migrations and
backed-up adoption of existing SQLite databases. PostgreSQL/pgvector integration
checks run in a separate CI job with deterministic embeddings; no API credits
are used. Locally, set `TEST_POSTGRES_URL` to an isolated disposable database to
run those checks.

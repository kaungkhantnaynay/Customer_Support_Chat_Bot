# Local Release Verification

## Render Free Plan Configuration - September 18, 2026

- `pytest -q`: 97 passed, 3 PostgreSQL-only checks skipped locally.
- `ruff check .`: passed.
- `render.yaml` passed Render's current official JSON Schema validation with the
  web service on the free plan and `DATABASE_URL` supplied at deployment time.
- Migration coverage verifies unrelated application tables are preserved when the
  support schema is installed into BeanCO's shared preview database.
- Verified the revised startup sequence applies migrations to a clean database,
  starts the API on the runtime port, and returns `200` from `/health`.
- Docker Desktop was not running, so the image was not rebuilt for this
  configuration-only verification. The same image was built and smoke-tested in
  the September 17 verification below; the only Dockerfile change is its startup
  command.

## BeanCO Render Preparation - September 17, 2026

- `pytest -q`: 96 passed, 3 PostgreSQL-only checks skipped locally.
- `ruff check .`: passed.
- Generic offline evaluation: 27 examples and 138/138 checks passed.
- BeanCO offline evaluation: 10 examples and 50/50 checks passed.
- `render.yaml` passed Render's current official JSON Schema validation.
- Built and ran the production image as non-root user `app`.
- Verified migrations on a clean database, runtime `PORT` binding, database-aware
  `/health`, a `401` response without `X-Support-Token`, and a grounded BeanCO answer
  with the correct token.
- The disposable container, volume, image, and evaluation outputs were removed or
  written outside the repository after verification.

## Portfolio Review - September 12, 2026

- `pytest -q`: 91 passed, 3 skipped.
- `ruff check .`: passed.
- Offline evaluation: 27 examples and 138/138 checks passed.
- Browser review: grounded shipping answer, duplicate-charge escalation, billing
  ticket dashboard, and OpenAPI documentation rendered successfully.
- Offline answers now expose only the citation used to construct the answer;
  `tests/test_chat.py` covers the exact shipping citation.
- Live OpenAI evaluation remains blocked by `credit_balance_exhausted`; no live
  cases completed and no semantic thresholds changed.

## Storage And Containers

- Built the Python 3.12 application image with locked runtime dependencies,
  Psycopg, pgvector, Alembic configuration, and migration scripts.
- Started a separate pgvector/PostgreSQL 17 Compose stack on localhost:18000.
- Verified the migration service completes before the application starts.
- Ran all eight PostgreSQL test-module checks against a separate disposable
  PostgreSQL database. These cover actual cosine ranking, index reuse after
  creating a new retriever, snapshot invalidation, invalid dimensions/batches,
  and chat/ticket persistence. Embeddings were deterministic test vectors.
- Backed up and migrated the local SQLite database; original support row counts
  were preserved.

## Browser Checks

Verified in Chrome against the containerized application backed by PostgreSQL,
using offline AI mode and synthetic customer data:

1. Asked an express-shipping question and received a source-cited answer.
2. Submitted helpful feedback and observed the saved confirmation.
3. Continued the chat with a duplicate-charge question and received a billing
   escalation with ticket ID.
4. Opened the authenticated admin workspace and found that ticket.
5. Changed its status to In progress and team to billing_specialists; the updated
   values appeared in the queue.
6. Filtered for Open tickets and observed the correct empty state.
7. Asked an unsupported musical-instrument question, received a refusal without
   citations, and observed a new escalation ticket.

Browser automation initially blocked the native HTTP Basic prompt. Signing in
with the disposable test credentials and then navigating to the clean URL
allowed the admin checks to proceed. This was a local test environment, not a
production login or live customer dataset.

The chat sidebar's obsolete fixed evaluation count and mode label were replaced
with general descriptions to avoid displaying stale system status.

## Limits

These are desktop functional smoke checks, not exhaustive accessibility,
responsive-layout, load, or security testing. Live OpenAI answer quality and
threshold calibration remain deferred. Hosted production verification still
depends on the deployment choice.

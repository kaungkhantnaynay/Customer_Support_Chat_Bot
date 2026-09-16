# Database Migrations And PostgreSQL Storage

## What Changed

Alembic now owns schema changes. Revision `0001` contains the frozen support
schema; `0002` adds persistent knowledge vectors and indexes for conversation
history, feedback references, and ticket queries. Runtime requests verify the
migration revision instead of creating tables.

SQLite remains supported for local development through SQLAlchemy's synchronous
driver. PostgreSQL uses the Psycopg 3 driver and SQLAlchemy connection pooling
with connection health checks. URLs starting with `postgres://` or
`postgresql://` are normalized to Psycopg without losing encoded passwords or
connection options. Older `sqlite+aiosqlite://` local URLs remain normalized for
compatibility, but new configuration uses `sqlite://`.

## Local Setup

For a new database:

```bash
uv sync --locked --group dev
uv run --locked python scripts/migrate_database.py
uv run --locked uvicorn app.main:app --reload
```

For an existing unversioned database, back up the file first, then run:

```bash
uv run --locked python scripts/migrate_database.py --adopt-legacy
```

Adoption compares the schema with the frozen baseline before stamping a revision.
Unexpected columns, tables, types, or indexes cause adoption to stop. A missing
conversation-access table from the older app is supported. Existing conversations
without access tokens still cannot be resumed, as documented in the README.

During this implementation the local SQLite database was backed up under
`reports/backups/`, migrated, and checked for unchanged conversation, message,
ticket, and feedback row counts. Backup files are ignored by Git and Docker.

Normal Alembic commands also work for versioned or empty databases:

```bash
uv run --locked alembic current
uv run --locked alembic upgrade head
```

Use the checked migration script for adopting legacy databases rather than
manually stamping an unknown schema. Downgrading from `0002` to `0001` removes
stored vectors and query indexes but preserves core support tables. Downgrading
to `base` removes support tables and data; it is not a deployment recovery plan.

## Docker

The SQLite demo stack runs a migration service before starting the app:

```bash
docker compose up --build
```

The PostgreSQL stack is a separate Compose file:

```bash
docker compose -f docker-compose.postgres.yml up --build
```

For that stack, set `POSTGRES_PASSWORD` in `.env` to a long URL-safe password
(letters, digits, hyphens, or underscores). Compose uses it both for PostgreSQL
and in the app's connection URL. Do not use this raw interpolation pattern for
passwords containing URL-reserved characters; for an external database, provide
a correctly encoded `DATABASE_URL` directly to the application.

The PostgreSQL service uses the pgvector-enabled PostgreSQL 17 image and a named
volume. It has no published database port. Both app stacks bind to localhost;
`SUPPORT_PORT` selects the host port (default 8000). Admin credentials are passed
from `.env`. The default AI mode remains offline.

For hosted deployments, run migrations once as a release step before starting
application replicas. Provision the vector extension using a database role with
permission to install it, then use appropriately restricted runtime credentials.
Include the hosting provider's required TLS options in `DATABASE_URL`.

## Persistent Semantic Retrieval

After live API access is restored, configure:

```dotenv
AI_MODE=openai
VECTOR_STORE=pgvector
DATABASE_URL=postgresql+psycopg://user:encoded-password@host:5432/database
OPENAI_API_KEY=your-key
```

For the Compose stack, it supplies its own internal database URL. Run migrations,
then explicitly index the knowledge base:

```bash
uv run --locked python scripts/index_knowledge.py
```

Or against a running PostgreSQL Compose stack:

```bash
docker compose -f docker-compose.postgres.yml exec support-ai \
  uv run --no-sync python scripts/index_knowledge.py
```

Indexing uses API credits when a new snapshot is needed. It is intentionally not
part of migrations, startup, tests, or deployment verification. No live OpenAI
requests were made during the storage work.

Each immutable snapshot is keyed by document contents, chunk metadata, and the
embedding model. All embeddings are inserted atomically. Repeating indexing for
an existing snapshot skips embedding generation. A new app instance reuses the
same stored vectors. Document/model changes require running indexing again;
unindexed snapshots cause chat to refuse and escalate rather than using stale
policy text. Old snapshots remain stored; retention cleanup is a future
operational task.

Search filters to the current snapshot and performs exact cosine ranking inside
PostgreSQL. The composite primary key indexes snapshot filtering. Exact search
is deliberate for this small knowledge base; approximate HNSW/IVFFlat indexes
should be evaluated when data volume justifies them. Vector dimensions are
validated on ingestion and query. SQLite's vector column is a schema-compatible
JSON placeholder, not a substitute for PostgreSQL semantic search.

## Verification

Tests cover empty-database migrations, repeat upgrades, schema/model agreement,
legacy adoption and data preservation, mismatched-schema rejection, and rollback
to the baseline. PostgreSQL integration tests use deterministic fake embeddings
to exercise actual pgvector insertion, cosine ranking, snapshot reuse and
invalidation, dimension checks, and chat/ticket persistence without API credits.

Run integration tests only against a dedicated disposable database:

```bash
TEST_POSTGRES_URL=postgresql+psycopg://user:password@localhost:5432/support_test \
  uv run --locked pytest tests/test_postgres.py -q
```

The tests clear knowledge-vector rows in that test database. With no test URL,
the three database-dependent tests skip. GitHub Actions now provides a separate
PostgreSQL service job so these checks run in CI.

References: [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html) and
[pgvector SQLAlchemy integration](https://github.com/pgvector/pgvector-python#sqlalchemy).

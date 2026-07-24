# Development Guide

## Environment

Dependencies are managed with `uv`.

```bash
uv sync --all-groups
```

Create a local environment file:

```bash
cp .env.example .env
```

## Run The API

```bash
uv run uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Quality Checks

```bash
uv run pytest
uv run ruff check .
```

## Current First Test

The foundation currently verifies:

- FastAPI app imports correctly.
- `/health` returns `{"status": "ok"}`.

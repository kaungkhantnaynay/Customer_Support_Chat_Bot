# Phase 1: Project Foundation

This phase created the basic project setup.

The goal was to prepare a clean Python backend project before building the AI chatbot features.

## Step 1: Created The Python Project

The project uses:

```text
Python
FastAPI
uv
pytest
ruff
```

The main project settings are stored in:

```text
pyproject.toml
```

This file controls:

- project name
- Python version
- installed packages
- testing settings
- linting rules

## Step 2: Installed Dependencies

Dependencies were installed using:

```bash
uv sync --all-groups
```

This created a local virtual environment:

```text
.venv/
```

That means this project has its own isolated Python packages.

## Step 3: Added The FastAPI App

The main app file is:

```text
app/main.py
```

It creates the FastAPI application and connects the API routes.

## Step 4: Added Basic Routes

The route file is:

```text
app/api/routes.py
```

The first endpoint was:

```text
GET /health
```

It returns:

```json
{
  "status": "ok"
}
```

This proves the backend is running correctly.

## Step 5: Added Environment Settings

The settings file is:

```text
app/core/config.py
```

It reads project settings such as:

- app name
- environment
- OpenAI API key
- database URL
- log level

The example environment file is:

```text
.env.example
```

Later, this can be copied to:

```text
.env
```

## Step 6: Added Testing

The first test file is:

```text
tests/test_health.py
```

It checks that:

- the app imports correctly
- `/health` returns a successful response

Tests are run with:

```bash
uv run pytest
```

## Step 7: Added Code Quality Checks

The project uses:

```text
ruff
```

Ruff checks Python code for style problems and common mistakes.

Run it with:

```bash
uv run ruff check .
```

## Step 8: Added Project Rules

The project rules are stored in:

```text
PROJECT_RULES.md
.codex/rules.md
```

These rules explain how we should build the project:

- keep code clean
- write tests
- keep routes small
- put business logic in services
- make AI answers grounded in documents
- avoid confident hallucinations

## Step 9: Added The Roadmap

The roadmap is stored in:

```text
TASKS.md
```

It breaks the project into phases:

- Foundation
- Knowledge Base
- Chat API
- Escalation and Tickets
- Evaluation
- Portfolio Polish

## Why This Phase Matters

Phase 1 does not build the chatbot yet.

Instead, it creates the professional project structure that makes the chatbot easier to build, test, explain, and show in a portfolio.

In simple terms:

```text
Phase 1 prepared the workspace and proved the backend can run.
```

## Result

At the end of Phase 1:

- dependencies were installed
- FastAPI was working
- `/health` endpoint was available
- tests were passing
- linting was clean
- rules and roadmap were documented

This gave us a stable base for Phase 2.

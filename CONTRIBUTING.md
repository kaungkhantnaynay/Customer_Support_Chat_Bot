# Contributing

## Engineering principles

- Keep route handlers thin and put business behavior in testable services.
- Validate HTTP contracts with Pydantic and keep database access behind SQLAlchemy.
- Retrieve evidence before generating answers and refuse unsupported requests.
- Keep deterministic escalation rules independent from model output.
- Add evaluation cases before materially changing prompts, retrieval, or thresholds.
- Never commit credentials, customer data, local databases, reports, or vector indexes.

## Development workflow

1. Choose an item from [the roadmap](docs/ROADMAP.md).
2. Make a focused change with tests and documentation.
3. Record architectural tradeoffs in `docs/ARCHITECTURE.md` or a focused design note.
4. Run the local quality gate before opening a pull request.

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run --locked python scripts/run_evaluation.py \
  --report reports/evaluation.json
```

Pull requests should explain the problem, solution, safety implications, evaluation
impact, verification performed, deployment changes, and remaining limitations.

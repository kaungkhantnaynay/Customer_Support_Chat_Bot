# Phase 5: Evaluation

This phase adds a small offline evaluation workflow for the support assistant.

The goal is to catch regressions in retrieval quality, citation behavior, refusal behavior, and escalation behavior before changing prompts or model logic.

## Step 1: Added Evaluation Dataset

I added evaluation examples in:

```text
data/evaluation/support_eval.jsonl
```

Each example defines:

- customer question
- expected knowledge base source ids
- required answer terms
- forbidden answer terms
- whether the assistant should refuse
- whether the conversation should escalate

The dataset covers:

- express shipping
- duplicate billing and refunds
- password reset help
- unknown out-of-scope questions

## Step 2: Added Evaluation Runner

I added deterministic evaluation logic in:

```text
app/evaluation/runner.py
```

The runner checks:

- expected retrieval sources are returned
- citations match expected source documents
- grounded answers include required support facts
- answers avoid forbidden unsupported claims
- unknown questions refuse without citations
- escalation decisions match the expected outcome

## Step 3: Added CI-Friendly Script

I added:

```text
scripts/run_evaluation.py
app/evaluation/cli.py
```

Run it with:

```bash
uv run python scripts/run_evaluation.py
```

The script prints a short pass/fail summary and exits with a non-zero status when any check fails.

That makes it suitable for CI.

## Step 4: Added Tests

I added:

```text
tests/test_evaluation.py
```

The tests verify that:

- the evaluation dataset loads
- the current retrieval and chat behavior passes all Phase 5 checks

## Why This Phase Matters

This phase gives the project a quality gate.

The assistant now has examples that protect the behavior users care about:

```text
Retrieve the right source -> answer with citations -> refuse weak context -> escalate risky cases
```

That is especially important before adding an LLM-backed answer generator, where regressions can be more subtle than ordinary API bugs.

## Next Phase

Next we can build Phase 6:

```text
Portfolio Polish
```

That phase should add a frontend chat UI, admin dashboard, Docker setup, screenshots, and deployment polish.

## Phase 7 Extension

The initial four examples have been expanded to 27, with separate category
results, conversation scenarios, strict input validation, JSON reports, and an
automated CI workflow. See [Phase 7](PHASE_7_QUALITY_AND_READINESS.md) for current
commands and behavior. The checks remain offline and heuristic.

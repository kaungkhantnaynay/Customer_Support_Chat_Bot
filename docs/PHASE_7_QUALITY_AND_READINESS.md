# Phase 7: Access Controls And Quality Checks

This phase follows the production-readiness checklist in `TASKS.md`. Access
controls and optional OpenAI generation were implemented first. This increment
expands the offline evaluation suite and adds automated CI.

## Evaluation Dataset

`data/evaluation/support_eval.jsonl` now contains 27 scenarios covering all five
knowledge-base topics: shipping, refunds, accounts, subscription/billing, and
troubleshooting. It includes routine questions, angry customers, technical
blockers, ambiguous requests, unsupported topics, and three conversation cases.

Each scenario declares its expected behavior before running the assistant:

- `expected_source_ids`: document IDs that retrieval and citations must include.
- `required_answer_terms` and `forbidden_answer_terms`: basic policy-content checks.
- `expect_refusal` and `expect_escalation`: expected support decisions.
- `history`: optional customer turns to send before the final question.

History cases test continuation in the same conversation, explicit follow-up
questions, topic changes, and refusal on an underspecified follow-up in offline
mode. They do not measure a live model's understanding of conversational context.
The separate mocked generation cases remain in `generation_cases.jsonl` and run
through pytest.

## Checks And Reports

The runner checks retrieval, citations, grounding, refusal, and escalation for
every scenario. History scenarios also check conversation continuity. This gives
138 checks across the 27 baseline scenarios.

Citation checks use actual retrieved citation labels and document IDs, including
titles that do not match filenames. Grounding checks detect missing required
phrases and forbidden claims, including in refusal responses. They are heuristic
checks, not a proof that every claim is supported.

Run from the repository root:

```bash
uv run --locked python scripts/run_evaluation.py --report reports/evaluation.json
```

Optional inputs:

```bash
uv run --locked python scripts/run_evaluation.py \
  --dataset data/evaluation/support_eval.jsonl \
  --knowledge-base data/knowledge_base \
  --report reports/evaluation.json
```

Console output includes separate category totals and individual failing checks.
JSON reports have `schema_version: 1` and `mode: offline`, aggregate and category
counts, and per-example questions, history, answers, retrieved chunk IDs/scores,
citations, confidence, escalation reasons, and check details.

Exit codes are 0 for success, 1 for failed quality checks, and 2 for invalid input
or report-writing errors. Empty datasets, duplicate IDs, invalid examples,
unknown expected sources, and missing knowledge bases cannot pass silently.
Configuration errors are also written to the requested report when possible.

Each scenario starts a fresh conversation in a temporary in-memory database.
The runner explicitly injects the offline engine, regardless of `AI_MODE`, and
never writes to the development database. Reports contain evaluation text and
should use synthetic examples. Generated reports are ignored by Git.

## Defects Found By The Expanded Dataset

- Offline answers truncated at 420 characters could omit account-deletion and
  technical-escalation instructions. The answer now preserves the complete chunk.
- The word `about` alone could make an ambiguous follow-up retrieve billing
  content. It is now excluded from keyword retrieval as a stop word.

These are narrow fixes backed by the new scenarios; the generation prompt was
not changed.

## Continuous Integration

`.github/workflows/quality.yml` runs on pushes, pull requests, and manual dispatch.
It uses Python 3.12 and 3.14, installs locked runtime and development dependencies,
and runs Ruff, pytest, and offline evaluation. It explicitly sets offline mode
and an empty API key and requires no repository secrets.

Test and evaluation steps still run after a lint failure if dependency installation
succeeded. Evaluation JSON is uploaded separately for each Python version, even
when quality checks fail, and retained for 14 days. The workflow has read-only
repository permissions and does not publish or deploy anything.

Local checks validate the code and report behavior. A successful hosted workflow
run can only be confirmed after the workflow is pushed to GitHub with Actions enabled.

Workflow references:
[uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/) and
[artifact upload action](https://github.com/actions/upload-artifact).

## Remaining Work

Live-model evaluation and semantic threshold calibration are still outstanding.
Production database migrations, PostgreSQL/pgvector, and desktop browser/Docker
smoke checks are now implemented and verified; see `PRODUCTION_STORAGE.md` and
`VERIFICATION.md`. Deployment remains outstanding. Final screenshots depend on the
standalone-versus-BeanCo decision documented in Phase 6.

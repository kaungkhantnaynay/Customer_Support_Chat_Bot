# Live AI Evaluation

## Status

The live evaluator is implemented and covered by mocked tests. An API key is now
configured, but the smoke run stopped at the first embedding request. OpenAI
returned HTTP 429 with code `credit_balance_exhausted` and type
`insufficient_quota`. Zero evaluation cases completed. The error report is saved
locally at `reports/live-smoke.json`.

The first successful live run and threshold calibration remain pending until API
credits are available. No thresholds were changed. Do not treat mock results or
the offline suite as live model-quality evidence.

## Run

Add a valid `OPENAI_API_KEY` to the local `.env` file. Do not paste it into chat
or commit it. The evaluator explicitly constructs the OpenAI engine, so the
application can remain in `AI_MODE=offline`.

From the repository root, begin with a two-example smoke check:

```bash
uv run --locked python scripts/run_live_evaluation.py \
  --limit 2 --max-calls 10 --report reports/live-smoke.json
```

Then run the full 18-case suite:

```bash
uv run --locked python scripts/run_live_evaluation.py \
  --limit 18 --max-calls 80 --report reports/live-baseline.json
```

These commands use API credits. The cap counts attempted embedding, generation,
and grading requests; it is not a dollar budget. Automatic retries are disabled.
Generation and grading have bounded output lengths and use the configured
request timeout. Reports record observed token usage but do not estimate pricing.

Exit codes are 0 for passing automated checks, 1 for quality failures, and 2 for
setup/provider/budget errors. A zero exit code still requires human review of the
answers and the grader's explanations.

## Dataset And Checks

`data/evaluation/live_eval.jsonl` contains eight calibration cases and ten
held-out validation cases. They cover all five knowledge-base topics,
paraphrases, an actual pronoun follow-up, unsupported questions, prompt injection,
account actions, and an unsupported delivery guarantee.

Live cases specify required facts rather than exact answer wording.
`source_ids` labels documents relevant to retrieval; a refusal may still have
relevant documents (for example, a password policy must not cause the assistant
to reveal an administrator password).

The evaluator runs the existing ChatService in a temporary in-memory database.
A recording retriever saves the actual query used by the service, including
follow-up context, and all chunk scores before applying the configured cutoff.
The generation prompt and production escalation rules are unchanged.

Deterministic checks verify refusal state, escalation, source membership, and
conversation continuity. A structured model grader checks whether cited source
text supports the answer and whether required facts are covered. It uses the
configured chat model; this can introduce correlated errors and self-grading
bias. Its scores are advisory evidence and must be reviewed by a person.
Malformed generation, invented source IDs, incomplete output, provider failures,
and request-budget exhaustion stop the run as errors rather than counting as
successful refusals.

## Reports

Reports are saved after each completed scenario, preserving partial progress.
They include model names, thresholds, hashes of the dataset/knowledge/generation
prompt, actual queries, ranked scores, answers, citations, confidence, escalation
reasons, checks, grader explanations, request counts, usage, and elapsed time.
Provider exception messages are not copied into reports. Generated report files
are ignored by Git. Evaluation data is synthetic and never touches the app's
local database.

Use a different report path for each baseline or candidate run. Reports are
replaced at the supplied path; automatic resume is not implemented.

## Threshold Review

The report sweeps minimum retrieval thresholds from 0.00 to 1.00 in increments
of 0.05. It minimizes retrieval misses plus false acceptances on calibration
cases only; ties favor fewer false acceptances and then the lower threshold.
The selected cutoff is also measured on held-out validation cases.

This analysis reuses recorded scores and makes no additional API requests. It
measures retrieval at the candidate cutoff, not how generated answers would
change. It does not modify settings. Inspect the answer failures and rerun the
live suite at a promising candidate, for example:

```bash
SEMANTIC_MIN_SCORE=0.40 uv run --locked python scripts/run_live_evaluation.py \
  --report reports/live-candidate.json
```

The example value is illustrative, not a recommendation. The configured high
threshold must be at least the minimum. High-confidence calibration remains a
separate review: compare actual correctness of high-confidence answers on a
larger labeled sample. This small initial suite is insufficient to establish a
reliable confidence probability or production-level safety.

The current validation split must remain untouched while choosing a candidate.
If failures influence further tuning, add fresh held-out cases before claiming
independent validation.

## Offline CI Remains Separate

`run_evaluation.py` and the GitHub Actions workflow remain strictly offline.
Pytest exercises the live evaluator with injected mock clients, including
budget limits, provider errors, JSON reports, and calibration/validation
separation. It never automatically initiates a live run.

Reference: [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

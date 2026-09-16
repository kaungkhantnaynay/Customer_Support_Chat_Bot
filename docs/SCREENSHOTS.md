# Portfolio Screenshots

The standalone UI in this repository is the selected portfolio surface. The final
review set was captured on September 12, 2026 against a clean local SQLite
database with `AI_MODE=offline`.

## Captured Shots

- Chat workspace answering “How long does express shipping take?” with the single
  Shipping Policy citation used by the answer.
- Chat workspace escalating “Can I get a refund if I was charged twice?” with a
  high-confidence answer, Refund Policy citation, and ticket `#1`.
- Authenticated admin dashboard showing ticket `#1` in the billing queue with
  high priority and open status.
- OpenAPI documentation showing the health, knowledge search, chat, feedback,
  and protected admin endpoint groups.
- VS Code terminal output showing 27 examples and 138/138 offline checks passing.

The screenshots use synthetic support questions and contain no API keys or
customer data. The live OpenAI result is deliberately excluded because the
provider stopped before completing a case; see `docs/LIVE_AI_EVALUATION.md`.

## Local Demo URLs

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/admin
http://127.0.0.1:8000/docs
```

## Portfolio Caption

```text
AI customer support assistant with retrieval-grounded answers, citations, deterministic escalation, human ticket review, and CI-friendly evaluation checks.
```

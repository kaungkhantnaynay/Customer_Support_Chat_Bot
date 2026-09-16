# BeanCO Storefront Integration

The support service includes a BeanCO-specific knowledge and evaluation pack without changing the generic portfolio benchmark.

## Run the support service for BeanCO

Use a separate port because BeanCO's Django API uses port 8000 locally:

```bash
KNOWLEDGE_BASE_DIR=data/knowledge_beanco \
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The BeanCO Next.js server connects through its own same-origin `/api/support/chat` route. Configure its server-only environment variable:

```dotenv
SUPPORT_API_BASE_URL=http://127.0.0.1:8001
```

Do not expose `SUPPORT_API_BASE_URL` with a `NEXT_PUBLIC_` prefix. Conversation access tokens pass only between the browser, the BeanCO same-origin route, and this service. The widget keeps its token in memory and does not store it in browser storage.

## Verify the BeanCO knowledge pack

```bash
uv run --locked python scripts/run_evaluation.py \
  --dataset data/evaluation/beanco_eval.jsonl \
  --knowledge-base data/knowledge_beanco \
  --report reports/beanco-evaluation.json
```

The knowledge pack describes only behavior already implemented and documented by BeanCO. Private order or account inspection, payment disputes, refunds requiring review, and account-ownership questions continue to create human-support tickets.

## Production boundary

Deploy the support service as a private or separately protected backend where possible, and point BeanCO's server-side `SUPPORT_API_BASE_URL` at it. Keep the support database, admin credentials, OpenAI key, and model settings on the support service. BeanCO's browser never receives those values.

Production launch still requires a chosen hosting target, HTTPS, secrets provisioning, database migrations, monitoring, and the live-model calibration described in `LIVE_AI_EVALUATION.md`.

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
SUPPORT_API_TOKEN=replace-with-a-shared-random-secret
```

Configure the same `SUPPORT_API_TOKEN` in this service. When it is set, chat,
feedback, and knowledge-search requests require the `X-Support-Token` header sent by
BeanCO's server-side proxy. Do not expose either setting with a `NEXT_PUBLIC_` prefix.
Conversation access tokens pass only between the browser, the BeanCO same-origin
route, and this service. The widget keeps its token in memory and does not store it in
browser storage.

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

The checked-in Render Blueprint, deployment sequence, secrets, and operator actions are
documented in [Render deployment](RENDER_DEPLOYMENT.md). Production launch still
requires approving the displayed provider cost, creating the resources, configuring
Vercel, monitoring, and the live-model calibration described in
`LIVE_AI_EVALUATION.md`.

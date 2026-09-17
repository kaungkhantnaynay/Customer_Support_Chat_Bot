# Render Deployment For BeanCO Support

The repository includes `render.yaml` for a dedicated FastAPI web service and
PostgreSQL database in Render's Singapore region. It places both resources in the
existing `BeanCo` project's `Production` environment without managing the existing
Django API or database. Creating the Blueprint provisions paid resources; review
Render's current pricing before approving the plan.

The Blueprint configures:

- `beanco-support-api` using the Dockerfile and the BeanCO knowledge pack;
- a non-root application process with Render's runtime `PORT`;
- `beanco-support-db` on PostgreSQL 18 with no public database access;
- database migrations as a pre-deploy command;
- a database-aware `/health` deployment check;
- generated `ADMIN_PASSWORD` and `SUPPORT_API_TOKEN` secrets; and
- offline retrieval for the initial deployment, so launch verification makes no
  OpenAI requests.

## Before Creating The Blueprint

1. Confirm the repository's GitHub checks pass on the deployment commit.
2. Review the web-service and database prices shown by Render.
3. Keep the database separate from BeanCO's Django database.

## After The First Successful Deployment

1. Copy the generated `SUPPORT_API_TOKEN` from Render's support service variables.
2. In Vercel, set `SUPPORT_API_BASE_URL` to the service's HTTPS origin and set
   `SUPPORT_API_TOKEN` to the same secret for Production and Preview as appropriate.
3. Redeploy BeanCO and verify a new chat plus a follow-up question.
4. Verify `/admin` with the generated admin password and rotate it to an operator-owned
   value if required.
5. Configure a Vercel firewall rate limit for `POST /api/support/chat` before public
   launch. In-process counters are deliberately not used because they are unreliable
   across serverless instances.

Do not place either secret in a `NEXT_PUBLIC_` variable. The support database uses
Render's private connection string and should remain closed to public network access.

## Enabling OpenAI After Offline Verification

Complete the bounded live evaluation before changing the service to:

```dotenv
AI_MODE=openai
VECTOR_STORE=pgvector
OPENAI_API_KEY=<secret>
```

Then run `uv run --no-sync python scripts/index_knowledge.py` as a one-off Render
command. The migration enables the `vector` extension, and indexing stores the
current BeanCO knowledge snapshot before semantic chat traffic is enabled.

# Render Deployment For BeanCO Support

The repository includes `render.yaml` for a dedicated FastAPI web service in Render's
Singapore region. It places the service in the existing `BeanCo` project's
`Production` environment without managing the existing Django API or database. The
Blueprint uses Render's free web plan and connects to BeanCO's existing free preview
database for an initial demo deployment. Separate and upgrade both resources before
treating the service as production-ready.

The Blueprint configures:

- `beanco-support-api` using the Dockerfile and the BeanCO knowledge pack;
- a non-root application process with Render's runtime `PORT`;
- a required `DATABASE_URL` supplied from the existing `beanco-preview-db` internal
  connection URL during Blueprint creation;
- database migrations during container startup because free web services do not
  support pre-deploy commands;
- a database-aware `/health` deployment check;
- generated `ADMIN_PASSWORD` and `SUPPORT_API_TOKEN` secrets; and
- offline retrieval for the initial deployment, so launch verification makes no
  OpenAI requests.

## Before Creating The Blueprint

1. Confirm the repository's GitHub checks pass on the deployment commit.
2. Copy the internal connection URL from `beanco-preview-db`; provide it only in
   Render's `DATABASE_URL` secret field during Blueprint creation.
3. Confirm the database has enough room for the small support dataset.

## Free Plan Limits

- The web service spins down after 15 minutes without inbound traffic. Its first
  request after that has a cold start.
- The shared database is limited to 1 GB, has no managed backups, and expires after
  30 days. Render provides a further 14-day upgrade grace period before deletion.
- Render grants 750 free instance hours per workspace each month.

These limits and the shared database are suitable for testing and demonstrations,
not a dependable public store. The support migrations recognize only support-owned
table names and leave Django's prefixed tables untouched. Move the support service to
its own paid database before public launch, and upgrade before the preview database
expires if any data must be retained.

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
command after upgrading the web service, because free web services do not provide
shell access. The migration enables the `vector` extension, and indexing stores the
current BeanCO knowledge snapshot before semantic chat traffic is enabled.

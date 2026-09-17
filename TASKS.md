# Project Tasks

## Phase 1: Foundation

- [x] Create Python project structure.
- [x] Add dependency management with `uv`.
- [x] Add FastAPI application entrypoint.
- [x] Add environment-based settings.
- [x] Add project rules and portfolio goals.
- [x] Install dependencies into a local virtual environment.
- [x] Run first health-check test.

## Phase 2: Knowledge Base

- [x] Add sample support documents.
- [x] Build document loader and chunker.
- [x] Add embedding service interface.
- [x] Add local vector search implementation.
- [x] Return source citations from retrieval.

## Phase 3: Chat API

- [x] Add `/chat` endpoint.
- [x] Store conversations and messages.
- [x] Add grounded response prompt.
- [x] Add refusal behavior when context is missing.
- [x] Add user feedback endpoint.

## Phase 4: Escalation And Tickets

- [x] Add intent and risk classification.
- [x] Add escalation rules.
- [x] Add ticket creation service.
- [x] Add admin ticket endpoints.

## Phase 5: Evaluation

- [x] Create evaluation dataset.
- [x] Add retrieval accuracy checks.
- [x] Add hallucination and citation checks.
- [x] Add CI-friendly evaluation script.

## Phase 6: Portfolio Polish

- [x] Add frontend chat UI.
- [x] Add admin dashboard.
- [x] Add Docker setup.
- [x] Add architecture diagram and screenshot plan.
- [x] Capture final screenshots using the standalone UI.
- [ ] Deploy backend and frontend after choosing a production target.

## Phase 7: Access Controls And Production Readiness

- [x] Protect admin pages and ticket APIs with configured credentials; disable when unset.
- [x] Require conversation access tokens for follow-up messages and feedback.
- [x] Validate feedback message ownership and assistant role.
- [x] Escape customer-controlled content in the admin dashboard.
- [x] Isolate API tests from the local development database.
- [x] Add semantic embeddings and grounded model generation.
- [x] Include conversation context in generated answers.
- [x] Expand evaluation coverage to 27 scenarios across all five topics and follow-ups.
- [x] Add category totals and machine-readable evaluation reports.
- [x] Add automated CI for tests, lint, and evaluations.
- [x] Add production database migrations and PostgreSQL/pgvector integration.
- [x] Verify desktop chat/admin flows and the Docker build (see docs/VERIFICATION.md).
- [x] Add bounded live evaluation tooling, a held-out dataset, and threshold analysis.
- [x] Remove machine-specific editor metadata and unused evaluation/async dependencies.
- [ ] Run live OpenAI quality evaluation and calibrate semantic confidence thresholds (blocked by exhausted API credit balance).

## Phase 8: BeanCO Integration

- [x] Add a BeanCO-specific knowledge pack without changing the generic benchmark corpus.
- [x] Add a BeanCO offline evaluation dataset.
- [x] Document the same-origin storefront integration and server-only configuration boundary.
- [x] Connect the BeanCO storefront through its Next.js server and add an accessible support widget.
- [x] Prepare a secured Render deployment blueprint and Vercel service-token boundary.
- [ ] Deploy the support service and set BeanCO's production `SUPPORT_API_BASE_URL` after hosting is chosen.

# Project Rules

## Engineering Principles

- Keep the project portfolio-ready: readable code, clear boundaries, useful tests, and documented tradeoffs.
- Prefer small, inspectable services over one large chatbot script.
- Keep AI behavior grounded in retrieved context.
- Make the assistant say it does not know when retrieved evidence is weak.
- Store enough metadata to debug AI behavior: query, retrieved sources, model response, confidence, and escalation reason.

## Python Standards

- Use FastAPI for HTTP APIs.
- Use Pydantic models for request and response contracts.
- Use SQLAlchemy for database access.
- Keep business logic outside route handlers.
- Use dependency injection for settings, database sessions, and AI clients.
- Use `pytest` for tests and `ruff` for linting.

## AI Engineering Standards

- Retrieval comes before generation for knowledge-base questions.
- Responses should include source citations when grounded in documents.
- Escalate billing, account-specific, angry, or low-confidence requests.
- Avoid sending private secrets or unnecessary user data to the model.
- Add evaluation examples before changing prompts substantially.

## Git And Delivery Standards

- Keep commits focused by phase.
- Update `TASKS.md` when a phase item is completed.
- Update `README.md` when setup or behavior changes.
- Do not commit `.env`, local databases, vector stores, or virtual environments.

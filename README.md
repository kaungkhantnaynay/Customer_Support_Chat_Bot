# Customer Support AI

Portfolio-grade customer support assistant built with Python, FastAPI, RAG, escalation logic, and evaluation workflows.

## Goal

Build a realistic AI support system that can:

- Answer customer questions using a knowledge base.
- Cite retrieved sources.
- Escalate risky or low-confidence conversations to a human ticket queue.
- Store conversations and feedback.
- Provide admin analytics.
- Run automated tests and AI evaluation checks.

## Planned Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL + pgvector in production
- SQLite for local development
- OpenAI API for generation and embeddings
- pytest + Ruff
- Ragas or custom eval scripts for RAG quality checks

## Quick Start

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Project Status

Step 1 is project setup. The initial app exposes health and metadata endpoints while the RAG, database, chat, and evaluation layers are added step by step.

Step 2 adds a searchable local knowledge base with sample support documents, chunking, local keyword-vector retrieval, and source citations.

Step 3 adds a grounded chat API, local conversation/message storage, refusal behavior for weak context, and user feedback capture.

Step 4 adds deterministic escalation rules, automatic ticket creation, and admin ticket endpoints.

## Current Endpoints

```text
GET /health
GET /knowledge/search?q=refund
POST /chat
POST /feedback
GET /admin/tickets
GET /admin/tickets/{ticket_id}
PATCH /admin/tickets/{ticket_id}
```

Read the phase explanations here:

```text
docs/PHASE_1_FOUNDATION.md
docs/PHASE_2_KNOWLEDGE_BASE.md
docs/PHASE_3_CHAT_API.md
docs/PHASE_4_ESCALATION_AND_TICKETS.md
```

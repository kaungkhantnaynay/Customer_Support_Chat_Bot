# Phase 3: Chat API

This phase turns the searchable knowledge base into a customer-facing chat API.

The goal was to keep the assistant grounded in support documents before adding a real language model.

## Step 1: Added Chat Request And Response Schemas

I added chat API contracts in:

```text
app/schemas/chat.py
```

The chat request accepts:

- customer message
- optional conversation id

The chat response returns:

- conversation id
- assistant message id
- grounded answer
- citations
- confidence
- escalation flag
- escalation reason when needed

## Step 2: Added Conversation Storage

I added a small SQLAlchemy persistence layer in:

```text
app/db/models.py
app/db/session.py
```

The first local database tables are:

- conversations
- messages
- feedback

Local development uses SQLite through the existing `DATABASE_URL` setting.

## Step 3: Added The Chat Service

The main chat logic lives in:

```text
app/services/chat.py
```

The route does not build the answer directly.

Instead, the service:

1. Creates or loads a conversation.
2. Stores the customer message.
3. Searches the knowledge base.
4. Builds a source-grounded answer.
5. Stores the assistant message.
6. Returns answer metadata.

## Step 4: Added Grounded Response Behavior

For this phase, the assistant uses a deterministic local answer builder instead of calling OpenAI.

That keeps development easy because:

- tests do not need an API key
- responses are predictable
- retrieval behavior can be debugged first
- an OpenAI-backed generator can be added later behind the same service boundary

When sources are strong enough, the answer includes source citations.

When sources are missing or weak, the assistant refuses to guess.

Example refusal:

```text
I do not have enough information in the support knowledge base to answer that.
```

## Step 5: Added Feedback Endpoint

I added:

```text
POST /feedback
```

This records customer feedback with:

- conversation id
- optional message id
- rating
- comment

This prepares the project for later evaluation and admin analytics.

## Step 6: Improved Local Retrieval

I added stop-word filtering to the local keyword embedding service.

This makes the local retriever focus more on meaningful support terms instead of common words such as:

```text
if
the
can
your
```

That improved matching for questions like duplicate billing and refunds.

## Step 7: Added Tests

I added:

```text
tests/test_chat.py
```

The tests verify that:

- `/chat` returns grounded answers with citations
- unknown questions get a refusal
- existing conversations can continue
- `/feedback` records customer feedback
- short chat messages fail validation

## Current Endpoints

```text
GET /health
GET /knowledge/search?q=refund
POST /chat
POST /feedback
```

## Example Chat Request

```json
{
  "message": "Can I get a refund if I was charged twice?"
}
```

## Example Chat Response

```json
{
  "conversation_id": 1,
  "message_id": 2,
  "answer": "Based on Refund Policy...",
  "citations": ["Refund Policy (data/knowledge_base/refund_policy.md)"],
  "confidence": "high",
  "needs_escalation": false,
  "escalation_reason": null
}
```

## Why This Phase Matters

This phase creates the first real chatbot experience.

It still does not depend on model generation, but it proves the most important support-assistant behavior:

```text
Search trusted knowledge first, answer with citations, and refuse when evidence is weak.
```

That makes the next AI step safer because generation can be added after the grounding rules are already tested.

## Next Phase

Next we can build Phase 4:

```text
Escalation And Tickets
```

That phase should add stronger intent and risk classification, ticket creation, and admin ticket endpoints.

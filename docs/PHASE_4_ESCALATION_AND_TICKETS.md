# Phase 4: Escalation And Tickets

This phase turns escalation decisions into real support tickets.

The goal was to make the project feel more like a customer support platform, not only a chat API.

## Step 1: Added Ticket Storage

I added a ticket model in:

```text
app/db/models.py
```

Tickets store:

- conversation id
- assistant message id
- status
- priority
- escalation reason
- customer message
- assigned team
- created timestamp
- updated timestamp

## Step 2: Added Ticket Schemas

I added ticket API contracts in:

```text
app/schemas/ticket.py
```

The schemas define:

- ticket response shape
- ticket list response shape
- ticket update request shape
- allowed ticket statuses
- allowed priorities

## Step 3: Added Intent And Risk Classification

I added a deterministic escalation classifier in:

```text
app/services/escalation.py
```

For now, the classifier uses transparent rules instead of an AI model.

It escalates:

- low-confidence answers
- billing and refund issues
- duplicate charges
- account access issues
- angry customer messages
- technical blockers

This keeps behavior easy to test and explain.

## Step 4: Added Escalation Rules

The escalation service returns a decision with:

```text
needs_escalation
reason
priority
assigned_team
```

Examples:

```text
Duplicate billing -> high priority -> billing
Low confidence -> medium priority -> general_support
Angry customer -> high priority -> customer_success
Account access -> medium priority -> account_support
Technical blocker -> medium priority -> technical_support
```

## Step 5: Added Ticket Creation Service

I added ticket creation and admin ticket operations in:

```text
app/services/tickets.py
```

The chat service now creates a ticket automatically when escalation is required.

The chat response includes:

```text
ticket_id
needs_escalation
escalation_reason
```

## Step 6: Added Admin Ticket Endpoints

I added:

```text
GET /admin/tickets
GET /admin/tickets/{ticket_id}
PATCH /admin/tickets/{ticket_id}
```

Admins can:

- list tickets
- filter tickets by status
- inspect a ticket
- update ticket status
- reassign a ticket team

## Step 7: Added Tests

I updated:

```text
tests/test_chat.py
```

The tests verify that:

- routine knowledge questions do not create tickets
- duplicate billing creates a high-priority billing ticket
- missing context creates an escalation ticket
- admins can list tickets
- admins can update ticket status and assigned team
- missing tickets return 404

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

## Example Escalated Chat Request

```json
{
  "message": "I was charged twice. Can I get a refund?"
}
```

## Example Escalated Chat Response

```json
{
  "conversation_id": 1,
  "message_id": 2,
  "ticket_id": 1,
  "answer": "Based on Refund Policy...",
  "citations": ["Refund Policy (data/knowledge_base/refund_policy.md)"],
  "confidence": "high",
  "needs_escalation": true,
  "escalation_reason": "Billing or refund issue requires human review."
}
```

## Example Ticket Response

```json
{
  "id": 1,
  "conversation_id": 1,
  "message_id": 2,
  "status": "open",
  "priority": "high",
  "reason": "Billing or refund issue requires human review.",
  "customer_message": "I was charged twice. Can I get a refund?",
  "assigned_team": "billing",
  "created_at": "2026-07-24T12:00:00",
  "updated_at": "2026-07-24T12:00:00"
}
```

## Why This Phase Matters

This phase adds operational behavior.

The assistant no longer only says that a request should be escalated.

It creates a support ticket that an admin workflow can inspect and update.

In simple terms:

```text
Risky support conversation -> escalation decision -> persisted ticket -> admin action
```

## Next Phase

Next we can build Phase 5:

```text
Evaluation
```

That phase should add test examples for retrieval quality, citation quality, refusal behavior, and escalation correctness.

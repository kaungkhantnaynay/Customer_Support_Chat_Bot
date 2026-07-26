from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    conversation_id: int | None = Field(default=None, ge=1)


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    ticket_id: int | None = None
    answer: str
    citations: list[str]
    confidence: Confidence
    needs_escalation: bool
    escalation_reason: str | None = None


class FeedbackRequest(BaseModel):
    conversation_id: int = Field(ge=1)
    message_id: int | None = Field(default=None, ge=1)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    feedback_id: int
    status: str

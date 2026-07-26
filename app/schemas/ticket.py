from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]


class TicketResponse(BaseModel):
    id: int
    conversation_id: int
    message_id: int | None
    status: TicketStatus
    priority: TicketPriority
    reason: str
    customer_message: str
    assigned_team: str
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class TicketUpdateRequest(BaseModel):
    status: TicketStatus | None = None
    assigned_team: str | None = Field(default=None, min_length=2, max_length=80)

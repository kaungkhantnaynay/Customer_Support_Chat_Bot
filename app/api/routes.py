import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAIError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import require_admin, require_support_service, token_digest
from app.db.models import ConversationAccess, Message
from app.db.session import get_session
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from app.schemas.health import HealthResponse
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from app.schemas.ticket import TicketListResponse, TicketResponse, TicketUpdateRequest
from app.services.chat import ChatService
from app.services.engine import get_answer_engine
from app.services.tickets import TicketService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(session: Annotated[Session, Depends(get_session)]) -> HealthResponse:
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok")


@router.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": "Customer Support AI",
        "status": "setup-complete",
        "docs": "/docs",
    }


@router.get(
    "/knowledge/search",
    response_model=KnowledgeSearchResponse,
    tags=["knowledge"],
    dependencies=[Depends(require_support_service)],
)
def search_knowledge(
    q: str = Query(min_length=2, description="Customer question or search query."),
    limit: int = Query(default=3, ge=1, le=5),
) -> KnowledgeSearchResponse:
    try:
        engine = get_answer_engine()
        results = engine.knowledge_base.search(q, limit=limit, min_score=engine.min_score)
    except (OpenAIError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Knowledge search is unavailable.") from exc

    return KnowledgeSearchResponse(
        query=q,
        results=[
            KnowledgeSearchResult(
                score=round(result.score, 4),
                title=result.chunk.title,
                source_path=result.chunk.source_path,
                citation=result.citation,
                text=result.chunk.text,
            )
            for result in results
        ],
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["chat"],
    dependencies=[Depends(require_support_service)],
)
def chat(
    request: ChatRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ChatResponse:
    if request.conversation_id is not None:
        verify_conversation(session, request.conversation_id, request.conversation_token)
    service = ChatService(session)
    return service.answer(request)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["chat"],
    dependencies=[Depends(require_support_service)],
)
async def feedback(
    request: FeedbackRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FeedbackResponse:
    verify_conversation(session, request.conversation_id, request.conversation_token)
    if request.message_id is not None:
        message = session.get(Message, request.message_id)
        if (
            message is None
            or message.conversation_id != request.conversation_id
            or message.role != "assistant"
        ):
            raise HTTPException(status_code=422, detail="Invalid feedback message.")
    service = ChatService(session)
    return service.save_feedback(request)


@router.get(
    "/admin/tickets",
    response_model=TicketListResponse,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
async def list_tickets(
    session: Annotated[Session, Depends(get_session)],
    status: str | None = Query(default=None),
) -> TicketListResponse:
    service = TicketService(session)
    return service.list_tickets(status=status)


@router.get(
    "/admin/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
async def get_ticket(
    ticket_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> TicketResponse:
    service = TicketService(session)
    ticket = service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


@router.patch(
    "/admin/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
async def update_ticket(
    ticket_id: int,
    request: TicketUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> TicketResponse:
    service = TicketService(session)
    ticket = service.update_ticket(ticket_id, request)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


def verify_conversation(session: Session, conversation_id: int, token: str | None) -> None:
    access = session.get(ConversationAccess, conversation_id)
    if (
        access is None
        or token is None
        or not secrets.compare_digest(access.token_hash, token_digest(token))
    ):
        raise HTTPException(status_code=403, detail="Conversation access denied.")

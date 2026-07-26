from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_session
from app.rag.retriever import LocalKnowledgeBase
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from app.schemas.health import HealthResponse
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from app.schemas.ticket import TicketListResponse, TicketResponse, TicketUpdateRequest
from app.services.chat import ChatService
from app.services.tickets import TicketService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": "Customer Support AI",
        "status": "setup-complete",
        "docs": "/docs",
    }


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse, tags=["knowledge"])
async def search_knowledge(
    q: str = Query(min_length=2, description="Customer question or search query."),
    limit: int = Query(default=3, ge=1, le=5),
) -> KnowledgeSearchResponse:
    knowledge_base = LocalKnowledgeBase.from_directory(settings.knowledge_base_dir)
    results = knowledge_base.search(q, limit=limit)

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


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    session: Annotated[Session, Depends(get_session)],
) -> ChatResponse:
    service = ChatService(session)
    return service.answer(request)


@router.post("/feedback", response_model=FeedbackResponse, tags=["chat"])
async def feedback(
    request: FeedbackRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FeedbackResponse:
    service = ChatService(session)
    return service.save_feedback(request)


@router.get("/admin/tickets", response_model=TicketListResponse, tags=["admin"])
async def list_tickets(
    session: Annotated[Session, Depends(get_session)],
    status: str | None = Query(default=None),
) -> TicketListResponse:
    service = TicketService(session)
    return service.list_tickets(status=status)


@router.get("/admin/tickets/{ticket_id}", response_model=TicketResponse, tags=["admin"])
async def get_ticket(
    ticket_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> TicketResponse:
    service = TicketService(session)
    ticket = service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


@router.patch("/admin/tickets/{ticket_id}", response_model=TicketResponse, tags=["admin"])
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

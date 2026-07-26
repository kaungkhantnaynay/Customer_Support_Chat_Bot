from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Ticket
from app.schemas.ticket import TicketListResponse, TicketResponse, TicketUpdateRequest
from app.services.escalation import EscalationDecision


class TicketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_ticket(
        self,
        conversation_id: int,
        message_id: int | None,
        customer_message: str,
        decision: EscalationDecision,
    ) -> Ticket:
        if not decision.needs_escalation or decision.reason is None:
            raise ValueError("Cannot create a ticket without an escalation reason.")

        ticket = Ticket(
            conversation_id=conversation_id,
            message_id=message_id,
            status="open",
            priority=decision.priority,
            reason=decision.reason,
            customer_message=customer_message,
            assigned_team=decision.assigned_team,
        )
        self.session.add(ticket)
        self.session.flush()
        return ticket

    def list_tickets(self, status: str | None = None) -> TicketListResponse:
        statement = select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc())
        if status is not None:
            statement = statement.where(Ticket.status == status)

        tickets = self.session.scalars(statement).all()
        return TicketListResponse(tickets=[self._to_response(ticket) for ticket in tickets])

    def get_ticket(self, ticket_id: int) -> TicketResponse | None:
        ticket = self.session.get(Ticket, ticket_id)
        if ticket is None:
            return None
        return self._to_response(ticket)

    def update_ticket(
        self,
        ticket_id: int,
        request: TicketUpdateRequest,
    ) -> TicketResponse | None:
        ticket = self.session.get(Ticket, ticket_id)
        if ticket is None:
            return None

        if request.status is not None:
            ticket.status = request.status
        if request.assigned_team is not None:
            ticket.assigned_team = request.assigned_team

        self.session.commit()
        self.session.refresh(ticket)
        return self._to_response(ticket)

    def _to_response(self, ticket: Ticket) -> TicketResponse:
        return TicketResponse(
            id=ticket.id,
            conversation_id=ticket.conversation_id,
            message_id=ticket.message_id,
            status=ticket.status,
            priority=ticket.priority,
            reason=ticket.reason,
            customer_message=ticket.customer_message,
            assigned_team=ticket.assigned_team,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )

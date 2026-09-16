import logging
import re
import secrets

from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import token_digest
from app.db.models import Conversation, ConversationAccess, Feedback, Message
from app.rag.retriever import RetrievalResult
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Confidence,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.engine import AnswerEngine, get_answer_engine
from app.services.escalation import EscalationService
from app.services.tickets import TicketService

MIN_GROUNDED_SCORE = 0.12
logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: Session, engine: AnswerEngine | None = None) -> None:
        self.session = session
        self.engine = engine
        self.escalation_service = EscalationService()
        self.ticket_service = TicketService(session)

    def answer(self, request: ChatRequest) -> ChatResponse:
        conversation = self._get_or_create_conversation(request.conversation_id)
        conversation_token = None
        if request.conversation_id is None:
            conversation_token = secrets.token_urlsafe(32)
            self.session.add(
                ConversationAccess(
                    conversation_id=conversation.id, token_hash=token_digest(conversation_token)
                )
            )
        history = self._history(conversation.id)
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
        self.session.add(user_message)

        answer, confidence, base_needs_escalation, base_escalation_reason, citations = (
            self._respond(request.message, history)
        )
        escalation_decision = self.escalation_service.classify(
            request.message,
            confidence,
            existing_reason=base_escalation_reason if base_needs_escalation else None,
        )

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            citations="\n".join(citations),
            confidence=confidence,
        )
        self.session.add(assistant_message)
        self.session.flush()

        ticket_id = None
        if escalation_decision.needs_escalation:
            ticket = self.ticket_service.create_ticket(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                customer_message=request.message,
                decision=escalation_decision,
            )
            ticket_id = ticket.id

        self.session.commit()
        self.session.refresh(assistant_message)

        return ChatResponse(
            conversation_token=conversation_token,
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            ticket_id=ticket_id,
            answer=answer,
            citations=citations,
            confidence=confidence,
            needs_escalation=escalation_decision.needs_escalation,
            escalation_reason=escalation_decision.reason,
        )

    def _history(self, conversation_id: int) -> list[dict[str, str]]:
        if settings.history_message_limit == 0:
            return []
        messages = self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(settings.history_message_limit)
        ).all()
        return [
            {"role": message.role, "content": message.content[:2000]}
            for message in reversed(messages)
        ]

    def _respond(
        self, question: str, history: list[dict[str, str]]
    ) -> tuple[str, Confidence, bool, str | None, list[str]]:
        try:
            engine = self.engine or get_answer_engine()
            query = question
            if (
                engine.generator
                and len(question) <= 120
                and re.search(r"\b(it|that|those|they|them|this)\b", question.lower())
            ):
                previous = next(
                    (
                        message["content"]
                        for message in reversed(history)
                        if message["role"] == "user"
                    ),
                    "",
                )
                query = f"{previous}\n{question}" if previous else question
            results = engine.knowledge_base.search(query, limit=3, min_score=engine.min_score)
            if engine.generator is None or not results:
                answer, confidence, escalate, reason = self._build_answer(question, results)
                citations = [results[0].citation] if results else []
                return answer, confidence, escalate, reason, citations
            generated = engine.generator.generate(question, results, history)
            sources = {result.chunk.id: result for result in results}
            if (
                generated.insufficient_context
                or not generated.answer.strip()
                or not generated.source_ids
                or any(source_id not in sources for source_id in generated.source_ids)
            ):
                return self._refusal("The generated answer could not be grounded in the sources.")
            selected = [sources[source_id] for source_id in dict.fromkeys(generated.source_ids)]
            citations = list(dict.fromkeys(result.citation for result in selected))
            confidence: Confidence = (
                "high"
                if min(result.score for result in selected) >= engine.high_score
                else "medium"
            )
            return (
                f"{generated.answer.strip()} Source: {'; '.join(citations)}",
                confidence,
                False,
                None,
                citations,
            )
        except (OpenAIError, ValueError) as exc:
            # Log only the exception type: provider errors may contain customer input.
            logger.warning("AI answer unavailable (%s)", type(exc).__name__)
            return self._refusal("The AI service could not produce a verified answer.")

    @staticmethod
    def _refusal(reason: str) -> tuple[str, Confidence, bool, str, list[str]]:
        return (
            "I cannot provide a verified answer right now. A support ticket has been created "
            "so a human can review your question.",
            "low",
            True,
            reason,
            [],
        )

    def save_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        feedback = Feedback(
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            rating=request.rating,
            comment=request.comment,
        )
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return FeedbackResponse(feedback_id=feedback.id, status="recorded")

    def _get_or_create_conversation(self, conversation_id: int | None) -> Conversation:
        if conversation_id is not None:
            conversation = self.session.get(Conversation, conversation_id)
            if conversation is not None:
                return conversation

        conversation = Conversation()
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def _build_answer(
        self,
        question: str,
        results: list[RetrievalResult],
    ) -> tuple[str, Confidence, bool, str | None]:
        if not results:
            return (
                "I do not have enough information in the support knowledge base to answer that.",
                "low",
                True,
                "No relevant knowledge base source was found.",
            )

        top_result = results[0]
        confidence = self._confidence_from_score(top_result.score)
        source_text = self._clean_source_text(top_result.chunk.text)
        answer = f"Based on {top_result.chunk.title}, {source_text} Source: {top_result.citation}"

        if confidence == "low":
            return (
                "I found a possible source, but it is not strong enough for a confident answer. "
                "Please contact support so a human can review this.",
                confidence,
                True,
                "Retrieved context was below the confidence threshold.",
            )

        return answer, confidence, False, None

    def _confidence_from_score(self, score: float) -> Confidence:
        if score >= 0.25:
            return "high"
        if score >= MIN_GROUNDED_SCORE:
            return "medium"
        return "low"

    def _clean_source_text(self, text: str) -> str:
        # Chunks already bound the context. Preserve complete policy statements rather
        # than cutting off qualifications or escalation instructions mid-sentence.
        return " ".join(text.split())

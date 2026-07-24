from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Feedback, Message
from app.rag.retriever import LocalKnowledgeBase, RetrievalResult
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Confidence,
    FeedbackRequest,
    FeedbackResponse,
)

MIN_GROUNDED_SCORE = 0.12


class ChatService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def answer(self, request: ChatRequest) -> ChatResponse:
        conversation = self._get_or_create_conversation(request.conversation_id)
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
        self.session.add(user_message)

        knowledge_base = LocalKnowledgeBase.from_directory(settings.knowledge_base_dir)
        results = knowledge_base.search(request.message, limit=3, min_score=MIN_GROUNDED_SCORE)
        answer, confidence, needs_escalation, escalation_reason = self._build_answer(
            request.message,
            results,
        )
        citations = [result.citation for result in results]

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            citations="\n".join(citations),
            confidence=confidence,
        )
        self.session.add(assistant_message)
        self.session.commit()
        self.session.refresh(assistant_message)

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=answer,
            citations=citations,
            confidence=confidence,
            needs_escalation=needs_escalation,
            escalation_reason=escalation_reason,
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
        answer = (
            f"Based on {top_result.chunk.title}, {source_text} "
            f"Source: {top_result.citation}"
        )

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
        normalized = " ".join(text.split())
        if len(normalized) <= 420:
            return normalized
        return f"{normalized[:417].rstrip()}..."

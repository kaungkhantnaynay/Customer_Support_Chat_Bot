from dataclasses import dataclass

from app.schemas.chat import Confidence


@dataclass(frozen=True)
class EscalationDecision:
    needs_escalation: bool
    reason: str | None = None
    priority: str = "low"
    assigned_team: str = "general_support"


class EscalationService:
    billing_terms = {
        "billing",
        "charged",
        "charge",
        "duplicate",
        "twice",
        "payment",
        "invoice",
        "refund",
        "subscription",
        "renewed",
    }
    account_terms = {
        "account",
        "login",
        "password",
        "locked",
        "email",
        "profile",
        "cannot access",
        "can't access",
    }
    anger_terms = {
        "angry",
        "furious",
        "unacceptable",
        "terrible",
        "cancel everything",
        "complaint",
    }
    technical_blocker_terms = {
        "bug",
        "broken",
        "blocked",
        "cannot use",
        "can't use",
        "paid feature",
        "dashboard does not load",
    }

    def classify(
        self,
        message: str,
        confidence: Confidence,
        existing_reason: str | None = None,
    ) -> EscalationDecision:
        normalized = message.lower()

        if confidence == "low":
            return EscalationDecision(
                needs_escalation=True,
                reason=existing_reason or "Retrieved context was not strong enough for an answer.",
                priority="medium",
                assigned_team="general_support",
            )

        if self._contains_any(normalized, self.anger_terms):
            return EscalationDecision(
                needs_escalation=True,
                reason="Customer sentiment indicates a human should review the conversation.",
                priority="high",
                assigned_team="customer_success",
            )

        if self._contains_any(normalized, self.billing_terms):
            return EscalationDecision(
                needs_escalation=True,
                reason="Billing or refund issue requires human review.",
                priority="high",
                assigned_team="billing",
            )

        if self._contains_any(normalized, self.account_terms):
            return EscalationDecision(
                needs_escalation=True,
                reason="Account-specific issue may require private customer verification.",
                priority="medium",
                assigned_team="account_support",
            )

        if self._contains_any(normalized, self.technical_blocker_terms):
            return EscalationDecision(
                needs_escalation=True,
                reason="Technical blocker may require support investigation.",
                priority="medium",
                assigned_team="technical_support",
            )

        return EscalationDecision(needs_escalation=False)

    def _contains_any(self, text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Base
from app.rag.retriever import LocalKnowledgeBase, RetrievalResult
from app.schemas.chat import ChatRequest
from app.services.chat import MIN_GROUNDED_SCORE, ChatService
from app.services.engine import AnswerEngine

DEFAULT_DATASET_PATH = Path("data/evaluation/support_eval.jsonl")


class EvaluationExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question: str = Field(min_length=2, max_length=2000)
    history: list[str] = Field(default_factory=list, max_length=10)
    expected_source_ids: list[str] = Field(default_factory=list)
    required_answer_terms: list[str] = Field(default_factory=list)
    forbidden_answer_terms: list[str] = Field(default_factory=list)
    expect_refusal: bool = False
    expect_escalation: bool = False

    @model_validator(mode="after")
    def validate_expectations(self) -> EvaluationExample:
        if not self.id.strip() or not self.question.strip():
            raise ValueError("Example ID and question must not be blank.")
        if any(len(turn.strip()) < 2 or len(turn) > 2000 for turn in self.history):
            raise ValueError("History turns must contain 2 to 2000 characters.")
        if self.expect_refusal and self.expected_source_ids:
            raise ValueError("Offline refusal cases must not require sources.")
        if not self.expect_refusal and not self.expected_source_ids:
            raise ValueError("Answer cases must specify expected sources.")
        return self


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class ExampleEvaluation:
    example_id: str
    checks: list[CheckResult]
    question: str
    history: list[str]
    answer: str
    retrieved_sources: list[dict[str, str | float]]
    citations: list[str]
    confidence: str
    escalation_reason: str | None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass(frozen=True)
class EvaluationSummary:
    examples: list[ExampleEvaluation]
    total_checks: int
    passed_checks: int
    failed_checks: int

    @property
    def passed(self) -> bool:
        return bool(self.examples) and self.failed_checks == 0

    @property
    def failed_examples(self) -> list[ExampleEvaluation]:
        return [example for example in self.examples if not example.passed]

    @property
    def categories(self) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for example in self.examples:
            for check in example.checks:
                group = counts.setdefault(check.name, {"passed": 0, "failed": 0, "total": 0})
                group["passed" if check.passed else "failed"] += 1
                group["total"] += 1
        return counts

    def to_report(self) -> dict:
        return {
            "schema_version": 1,
            "mode": "offline",
            "passed": self.passed,
            "total_examples": len(self.examples),
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "categories": self.categories,
            "examples": [
                {**asdict(example), "passed": example.passed} for example in self.examples
            ],
        }


def load_evaluation_dataset(path: Path = DEFAULT_DATASET_PATH) -> list[EvaluationExample]:
    examples: list[EvaluationExample] = []
    ids: set[str] = set()
    with path.open(encoding="utf-8") as dataset:
        for line_number, line in enumerate(dataset, start=1):
            if not line.strip():
                continue
            try:
                example = EvaluationExample.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid example on {path}:{line_number}: {exc}") from exc
            if example.id in ids:
                raise ValueError(f"Duplicate example ID '{example.id}' on {path}:{line_number}")
            ids.add(example.id)
            examples.append(example)
    if not examples:
        raise ValueError(f"Evaluation dataset is empty: {path}")
    return examples


def run_evaluation(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    knowledge_base_dir: Path | None = None,
) -> EvaluationSummary:
    examples = load_evaluation_dataset(dataset_path)
    knowledge_base = LocalKnowledgeBase.from_directory(
        knowledge_base_dir if knowledge_base_dir is not None else settings.knowledge_base_dir
    )
    if not knowledge_base.chunks:
        raise ValueError("Evaluation knowledge base is empty or missing.")
    known_sources = {chunk.document_id for chunk in knowledge_base.chunks}
    for example in examples:
        missing = set(example.expected_source_ids) - known_sources
        if missing:
            raise ValueError(f"Unknown expected sources for {example.id}: {sorted(missing)}")

    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(bind=engine)
        # Each example gets its own session and a new conversation, including history cases.
        evaluated_examples = []
        for example in examples:
            with Session(engine, expire_on_commit=False) as session:
                chat_service = ChatService(session, engine=AnswerEngine(knowledge_base))
                evaluated_examples.append(evaluate_example(example, knowledge_base, chat_service))
    finally:
        engine.dispose()

    total_checks = sum(len(example.checks) for example in evaluated_examples)
    passed_checks = sum(check.passed for example in evaluated_examples for check in example.checks)
    return EvaluationSummary(
        examples=evaluated_examples,
        total_checks=total_checks,
        passed_checks=passed_checks,
        failed_checks=total_checks - passed_checks,
    )


def evaluate_example(
    example: EvaluationExample,
    knowledge_base: LocalKnowledgeBase,
    chat_service: ChatService,
) -> ExampleEvaluation:
    conversation_id = None
    for turn in example.history:
        previous = chat_service.answer(ChatRequest(message=turn, conversation_id=conversation_id))
        conversation_id = previous.conversation_id
    results = knowledge_base.search(example.question, limit=3, min_score=MIN_GROUNDED_SCORE)
    response = chat_service.answer(
        ChatRequest(message=example.question, conversation_id=conversation_id)
    )

    retrieved_ids = {result.chunk.document_id for result in results}
    retrieval_passed = (
        not results if example.expect_refusal else set(example.expected_source_ids) <= retrieved_ids
    )
    valid_citations = {result.citation for result in results}
    cited_ids = {
        result.chunk.document_id for result in results if result.citation in response.citations
    }
    citations_passed = (
        not response.citations
        if example.expect_refusal
        else bool(response.citations)
        and set(response.citations) <= valid_citations
        and set(example.expected_source_ids) <= cited_ids
    )
    normalized = response.answer.lower()
    refused = any(
        marker in normalized
        for marker in (
            "do not have enough information",
            "not strong enough for a confident answer",
            "cannot provide a verified answer",
        )
    )
    checks = [
        CheckResult("retrieval", retrieval_passed, _source_details(results)),
        CheckResult("citations", citations_passed, f"citations={response.citations}"),
        _check_answer_grounding(example, response.answer, response.citations),
        CheckResult(
            "refusal",
            refused == example.expect_refusal,
            f"expected={example.expect_refusal}, actual={refused}",
        ),
        CheckResult(
            "escalation",
            response.needs_escalation == example.expect_escalation,
            f"expected={example.expect_escalation}, actual={response.needs_escalation}",
        ),
    ]
    if example.history:
        checks.append(
            CheckResult(
                "conversation",
                response.conversation_id == conversation_id,
                "Final response must continue the history conversation.",
            )
        )
    return ExampleEvaluation(
        example_id=example.id,
        checks=checks,
        question=example.question,
        history=example.history,
        answer=response.answer,
        retrieved_sources=[
            {
                "document_id": result.chunk.document_id,
                "chunk_id": result.chunk.id,
                "score": round(result.score, 6),
            }
            for result in results
        ],
        citations=response.citations,
        confidence=response.confidence,
        escalation_reason=response.escalation_reason,
    )


def _check_answer_grounding(
    example: EvaluationExample, answer: str, citations: list[str]
) -> CheckResult:
    normalized = answer.lower()
    missing = [term for term in example.required_answer_terms if term.lower() not in normalized]
    forbidden = [term for term in example.forbidden_answer_terms if term.lower() in normalized]
    source_marker = example.expect_refusal or (bool(citations) and "source:" in normalized)
    return CheckResult(
        "grounding",
        not missing and not forbidden and source_marker,
        f"missing_terms={missing}; forbidden_terms={forbidden}; source_marker_ok={source_marker}",
    )


def _source_details(results: list[RetrievalResult]) -> str:
    return (
        ", ".join(f"{result.chunk.document_id}:{result.score:.3f}" for result in results) or "none"
    )


def format_summary(summary: EvaluationSummary) -> str:
    status = "PASSED" if summary.passed else "FAILED"
    lines = [
        f"Evaluation {status} (offline)",
        f"Examples: {len(summary.examples)}",
        f"Checks: {summary.passed_checks} passed, {summary.failed_checks} failed",
    ]
    for category, counts in summary.categories.items():
        lines.append(f"  {category}: {counts['passed']}/{counts['total']} passed")
    for example in summary.failed_examples:
        lines.append(f"\n{example.example_id}")
        for check in example.checks:
            if not check.passed:
                lines.append(f"- {check.name}: {check.details}")
    return "\n".join(lines)

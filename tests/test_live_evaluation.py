import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APITimeoutError

from app.core.config import settings
from app.evaluation.live import (
    LiveRunError,
    MeteredClient,
    QualityGrade,
    load_live_dataset,
    run_live_evaluation,
    threshold_analysis,
)
from app.evaluation.live_cli import main
from app.services.generation import GeneratedAnswer


@pytest.fixture
def live_case(tmp_path, monkeypatch):
    knowledge = tmp_path / "kb"
    knowledge.mkdir()
    (knowledge / "shipping.md").write_text("# Shipping\n\nExpress delivery takes two days.")
    monkeypatch.setattr(settings, "knowledge_base_dir", knowledge)
    dataset = tmp_path / "live.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "express",
                "split": "calibration",
                "question": "Express delivery time?",
                "source_ids": ["shipping"],
                "required_facts": ["Two days."],
                "expect_escalation": False,
            }
        )
    )
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(index=0, embedding=[1.0, 0.0])],
        usage=SimpleNamespace(prompt_tokens=4),
    )
    generated = GeneratedAnswer(
        answer="Express delivery takes two days.",
        source_ids=["shipping::chunk-1"],
        insufficient_context=False,
    )
    grade = QualityGrade(supported=True, covers_required_facts=True, explanation="Supported.")

    def response(**kwargs):
        parsed = grade if kwargs["text_format"] is QualityGrade else generated
        return SimpleNamespace(
            status="completed",
            output_parsed=parsed,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )

    client.responses.parse.side_effect = response
    return dataset, tmp_path / "report.json", client


def test_live_success_uses_real_chat_and_records_scores_and_usage(live_case):
    dataset, report_path, client = live_case
    report = run_live_evaluation(report_path, dataset, client=client, progress=lambda _: None)
    assert report["status"] == "completed"
    assert report["passed"]
    assert report["mode"] == "live" and report["human_review_required"]
    assert report["requests"] == 4
    assert report["input_tokens"] == 28 and report["output_tokens"] == 10
    assert report["examples"][0]["ranked_sources"][0]["score"] == pytest.approx(1)
    assert report["examples"][0]["grade"]["supported"]
    saved = json.loads(report_path.read_text())
    assert saved == report
    assert "conversation_token" not in report_path.read_text()
    assert "api_key" not in report_path.read_text()
    client.close.assert_not_called()  # Injected clients remain owned by their caller.


def test_live_outage_cannot_pass_as_an_expected_refusal(live_case):
    dataset, report_path, client = live_case
    row = json.loads(dataset.read_text())
    row.update(expect_refusal=True, expect_escalation=True)
    dataset.write_text(json.dumps(row))
    client.responses.parse.side_effect = APITimeoutError(
        request=httpx.Request("POST", "https://example.test")
    )
    report = run_live_evaluation(report_path, dataset, client=client, progress=lambda _: None)
    assert report["status"] == "error" and not report["passed"]
    assert report["examples"] == []
    assert "APITimeoutError" in report["error"]


def test_live_request_budget_stops_before_next_call(live_case):
    dataset, report_path, client = live_case
    report = run_live_evaluation(
        report_path, dataset, max_calls=1, client=client, progress=lambda _: None
    )
    assert report["status"] == "error"
    assert report["requests"] == 1
    assert client.embeddings.create.call_count == 1
    client.responses.parse.assert_not_called()


def test_live_incomplete_generation_cannot_pass_refusal(live_case):
    dataset, report_path, client = live_case
    client.responses.parse.side_effect = None
    client.responses.parse.return_value = SimpleNamespace(
        status="incomplete",
        output_parsed=None,
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )
    report = run_live_evaluation(report_path, dataset, client=client, progress=lambda _: None)
    assert report["status"] == "error" and not report["passed"]


def test_live_negative_grade_fails_quality(live_case):
    dataset, report_path, client = live_case
    original = client.responses.parse.side_effect

    def response(**kwargs):
        result = original(**kwargs)
        if kwargs["text_format"] is QualityGrade:
            result.output_parsed = QualityGrade(
                supported=False, covers_required_facts=True, explanation="Unsupported promise."
            )
        return result

    client.responses.parse.side_effect = response
    report = run_live_evaluation(report_path, dataset, client=client, progress=lambda _: None)
    assert report["status"] == "completed" and not report["passed"]
    assert report["examples"][0]["checks"]["grounding"] is False


def test_live_missing_key_stops_before_client_creation(live_case, monkeypatch):
    dataset, report_path, _ = live_case
    monkeypatch.setattr(settings, "openai_api_key", "")
    constructor = Mock(side_effect=AssertionError("Should not create client"))
    monkeypatch.setattr("app.evaluation.live.OpenAI", constructor)
    assert main(["--dataset", str(dataset), "--report", str(report_path)]) == 2
    constructor.assert_not_called()


def test_live_report_is_writable_before_requests(live_case):
    dataset, report_path, client = live_case
    report_path.mkdir()
    with pytest.raises(OSError):
        run_live_evaluation(report_path, dataset, client=client)
    client.embeddings.create.assert_not_called()


def test_threshold_candidate_does_not_use_validation_labels():
    def row(split, ids, score):
        return {
            "split": split,
            "source_ids": ids,
            "ranked_sources": [{"document_id": "shipping", "score": score}],
        }

    calibration = [row("calibration", ["shipping"], 0.8), row("calibration", [], 0.2)]
    first = threshold_analysis(calibration + [row("validation", ["shipping"], 0.3)])
    second = threshold_analysis(calibration + [row("validation", [], 0.9)])
    assert first["candidate_min_score"] == second["candidate_min_score"] == 0.25
    assert first["validation_at_candidate"]["misses"] == 0
    assert second["validation_at_candidate"]["false_accepts"] == 1
    assert first["applied"] is False


def test_invalid_live_dataset_and_duplicate_ids(live_case):
    dataset, _, _ = live_case
    row = dataset.read_text()
    dataset.write_text(row + "\n" + row)
    with pytest.raises(ValueError, match="Duplicate"):
        load_live_dataset(dataset)
    dataset.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_live_dataset(dataset)


def test_meter_sanitizes_provider_errors():
    client = Mock()
    client.embeddings.create.side_effect = ValueError("secret provider payload")
    with pytest.raises(LiveRunError, match="ValueError") as exc:
        MeteredClient(client, 1).embeddings.create()
    assert "secret" not in str(exc.value)

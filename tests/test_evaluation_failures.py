import json

import pytest

from app.evaluation.cli import main
from app.evaluation.runner import load_evaluation_dataset, run_evaluation
from app.services.chat import ChatService


@pytest.mark.parametrize(
    "content,match",
    [
        ("\n", "empty"),
        ("not JSON", "Invalid example"),
        ('{"id":"bad","question":"A question"}', "expected sources"),
        ('{"id":"bad","question":"A question","expect_refusal":true,"typo":true}', "Extra inputs"),
    ],
)
def test_invalid_datasets_fail_instead_of_passing(tmp_path, content, match):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(content)
    with pytest.raises(ValueError, match=match):
        load_evaluation_dataset(dataset)


def test_duplicate_ids_are_rejected(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    row = json.dumps({"id": "same", "question": "Unknown?", "expect_refusal": True})
    dataset.write_text(f"{row}\n{row}\n")
    with pytest.raises(ValueError, match="Duplicate example ID"):
        load_evaluation_dataset(dataset)


@pytest.mark.parametrize(
    "change,category",
    [
        ({"citations": ["Fake citation"]}, "citations"),
        ({"answer": "Source: Shipping Policy. Guaranteed overnight delivery."}, "grounding"),
        ({"needs_escalation": True}, "escalation"),
        ({"answer": "I do not have enough information to answer that."}, "refusal"),
    ],
)
def test_quality_regressions_fail_reports_and_cli(monkeypatch, tmp_path, change, category):
    original = ChatService.answer

    def corrupted(self, request):
        return original(self, request).model_copy(update=change)

    monkeypatch.setattr(ChatService, "answer", corrupted)
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "shipping",
                "question": "How long does express shipping take?",
                "expected_source_ids": ["shipping_policy"],
                "required_answer_terms": ["1 to 2 business days"],
                "forbidden_answer_terms": ["overnight"],
            }
        )
    )
    report_path = tmp_path / "reports" / "quality.json"
    assert main(["--dataset", str(dataset), "--report", str(report_path)]) == 1
    report = json.loads(report_path.read_text())
    assert not report["passed"]
    assert report["categories"][category]["failed"] == 1
    assert not report["examples"][0]["passed"]
    assert any(not check["passed"] for check in report["examples"][0]["checks"])


def test_forbidden_terms_are_checked_in_refusals(monkeypatch):
    original = ChatService.answer

    def corrupted(self, request):
        response = original(self, request)
        if not response.citations:
            response = response.model_copy(
                update={"answer": response.answer + " Yes, we repair it."}
            )
        return response

    monkeypatch.setattr(ChatService, "answer", corrupted)
    summary = run_evaluation()
    example = next(item for item in summary.examples if item.example_id == "unknown_repair_request")
    assert not next(check for check in example.checks if check.name == "grounding").passed


def test_cli_writes_success_report(tmp_path):
    report_path = tmp_path / "report.json"
    assert main(["--report", str(report_path)]) == 0
    assert json.loads(report_path.read_text())["passed"]


def test_cli_writes_error_report_and_returns_two(tmp_path, capsys):
    dataset = tmp_path / "missing.jsonl"
    report_path = tmp_path / "report.json"
    assert main(["--dataset", str(dataset), "--report", str(report_path)]) == 2
    assert "Evaluation error" in capsys.readouterr().err
    report = json.loads(report_path.read_text())
    assert not report["passed"] and report["error"]


def test_unwritable_report_returns_two(tmp_path):
    # A directory is not a valid output file, regardless of filesystem permissions.
    assert main(["--report", str(tmp_path)]) == 2


def test_unknown_expected_source_is_a_configuration_error(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "invalid",
                "question": "Shipping?",
                "expected_source_ids": ["does_not_exist"],
            }
        )
    )
    with pytest.raises(ValueError, match="Unknown expected sources"):
        run_evaluation(dataset)


def test_missing_knowledge_base_is_a_configuration_error(tmp_path):
    with pytest.raises(ValueError, match="knowledge base is empty"):
        run_evaluation(knowledge_base_dir=tmp_path / "missing")

from pathlib import Path

from app.evaluation.runner import DEFAULT_DATASET_PATH, load_evaluation_dataset, run_evaluation


def test_loads_evaluation_dataset() -> None:
    examples = load_evaluation_dataset(DEFAULT_DATASET_PATH)

    assert len(examples) >= 4
    assert {example.id for example in examples} >= {
        "shipping_express_time",
        "refund_duplicate_charge",
        "unknown_repair_request",
    }


def test_phase_5_evaluation_passes_current_behavior() -> None:
    summary = run_evaluation(
        dataset_path=DEFAULT_DATASET_PATH,
        knowledge_base_dir=Path("data/knowledge_base"),
    )

    assert summary.passed
    assert summary.failed_checks == 0
    assert summary.passed_checks == summary.total_checks


def test_dataset_covers_every_topic_and_conversation_cases():
    examples = load_evaluation_dataset()
    assert {source for example in examples for source in example.expected_source_ids} == {
        "shipping_policy",
        "refund_policy",
        "account_help",
        "subscription_billing",
        "troubleshooting",
    }
    assert len(examples) >= 25
    assert sum(bool(example.history) for example in examples) >= 3
    assert any(example.expect_refusal for example in examples)
    assert any(not example.expect_escalation for example in examples)


def test_report_categories_and_totals_are_consistent():
    summary = run_evaluation()
    report = summary.to_report()
    assert report["schema_version"] == 1
    assert report["mode"] == "offline"
    assert report["passed"] is True
    assert set(report["categories"]) == {
        "retrieval",
        "citations",
        "grounding",
        "refusal",
        "escalation",
        "conversation",
    }
    assert sum(group["total"] for group in report["categories"].values()) == report["total_checks"]
    assert report["total_checks"] == report["passed_checks"] + report["failed_checks"]
    assert all(example["checks"] and example["answer"] for example in report["examples"])
    assert report["categories"]["conversation"]["total"] == 3


def test_real_titles_are_used_for_citations(tmp_path):
    import json

    knowledge = tmp_path / "kb"
    knowledge.mkdir()
    (knowledge / "policy.md").write_text("# Unrelated Title\n\nParcels arrive in five days.")
    dataset = tmp_path / "examples.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "custom-title",
                "question": "When do parcels arrive?",
                "expected_source_ids": ["policy"],
                "required_answer_terms": ["five days"],
            }
        )
    )
    assert run_evaluation(dataset, knowledge).passed


def test_history_turns_share_a_conversation_but_examples_do_not(monkeypatch, tmp_path):
    import json

    from app.services.chat import ChatService

    calls = []
    answer = ChatService.answer

    def record(self, request):
        response = answer(self, request)
        calls.append((request.conversation_id, response.conversation_id))
        return response

    monkeypatch.setattr(ChatService, "answer", record)
    dataset = tmp_path / "history.jsonl"
    example = {
        "question": "How long does express shipping take?",
        "expected_source_ids": ["shipping_policy"],
        "history": ["How long does standard shipping take?"],
    }
    dataset.write_text("\n".join(json.dumps({**example, "id": str(i)}) for i in range(2)))
    assert run_evaluation(dataset).passed
    assert calls[0][0] is None and calls[2][0] is None
    assert calls[1] == (calls[0][1], calls[0][1])
    assert calls[3] == (calls[2][1], calls[2][1])
    assert calls[0][1] != calls[2][1]

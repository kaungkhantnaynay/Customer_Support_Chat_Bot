import argparse
import json
import sys
from pathlib import Path

from app.evaluation.runner import DEFAULT_DATASET_PATH, format_summary, run_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run offline support quality checks (no API calls)."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--knowledge-base", type=Path, default=None)
    parser.add_argument("--report", type=Path, help="Write a JSON report, including failed checks.")
    args = parser.parse_args(argv)
    try:
        summary = run_evaluation(args.dataset, args.knowledge_base)
        report = summary.to_report()
        report["dataset"] = str(args.dataset)
        status = 0 if summary.passed else 1
        print(format_summary(summary))
    except (OSError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "mode": "offline",
            "passed": False,
            "dataset": str(args.dataset),
            "error": str(exc),
        }
        status = 2
        print(f"Evaluation error: {exc}", file=sys.stderr)
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Cannot write evaluation report: {exc}", file=sys.stderr)
            return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())

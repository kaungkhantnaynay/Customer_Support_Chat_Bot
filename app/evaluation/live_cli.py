import argparse
import json
import sys
from pathlib import Path

from app.evaluation.live import DEFAULT_LIVE_DATASET, run_live_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run live OpenAI evaluation (uses API credits).")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_LIVE_DATASET)
    parser.add_argument("--report", type=Path, default=Path("reports/live-evaluation.json"))
    parser.add_argument("--limit", type=int, default=18, help="Maximum examples (1..100).")
    parser.add_argument("--max-calls", type=int, default=80, help="Maximum API requests (1..500).")
    args = parser.parse_args(argv)
    try:
        report = run_live_evaluation(args.report, args.dataset, args.limit, args.max_calls)
    except (ValueError, OSError) as exc:
        print(f"Live evaluation could not start: {exc}", file=sys.stderr)
        return 2
    print(f"Live evaluation: {report['status']}")
    print(f"Examples: {len(report['examples'])}/{report['planned_examples']}")
    print(f"API requests: {report['requests']}")
    for example in report["examples"]:
        failed = [name for name, passed in example["checks"].items() if not passed]
        print(f"  {example['id']}: {'PASS' if not failed else ', '.join(failed)}")
    print(f"Report: {args.report}")
    if report["status"] == "error":
        print(report["error"], file=sys.stderr)
        return 2
    print(
        "Threshold analysis: "
        + json.dumps(report.get("threshold_analysis", {}).get("candidate_min_score"))
    )
    print("Automated grading requires human review; no thresholds were changed.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

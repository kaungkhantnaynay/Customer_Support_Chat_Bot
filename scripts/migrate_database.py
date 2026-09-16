import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.migrations import migrate  # noqa: E402
from app.db.session import engine  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply database migrations.")
    parser.add_argument(
        "--adopt-legacy",
        action="store_true",
        help="Validate and adopt an existing unversioned schema after backup.",
    )
    args = parser.parse_args()
    migrate(engine, adopt_legacy=args.adopt_legacy)
    print("Database migrations complete.")

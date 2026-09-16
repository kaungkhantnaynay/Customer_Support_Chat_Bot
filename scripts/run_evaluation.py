import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


if __name__ == "__main__":
    from app.evaluation.cli import main

    raise SystemExit(main())

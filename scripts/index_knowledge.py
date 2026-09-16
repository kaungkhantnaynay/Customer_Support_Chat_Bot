import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.migrations import require_current_schema  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.rag.postgres import PostgresKnowledgeBase  # noqa: E402
from app.services.engine import get_answer_engine  # noqa: E402

if __name__ == "__main__":
    if settings.vector_store != "pgvector":
        raise SystemExit("Set VECTOR_STORE=pgvector and configure PostgreSQL/OpenAI first.")
    require_current_schema(engine)
    store = get_answer_engine().knowledge_base
    if not isinstance(store, PostgresKnowledgeBase):
        raise SystemExit("PostgreSQL vector store is not configured.")
    changed = store.index()
    print("Knowledge snapshot indexed." if changed else "Knowledge snapshot already indexed.")

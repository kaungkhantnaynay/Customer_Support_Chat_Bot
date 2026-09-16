from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.migrations import require_current_schema
from app.db.urls import sync_database_url

engine = create_engine(sync_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_initialized = False


def init_db() -> None:
    global _initialized
    if _initialized:
        return

    require_current_schema(engine)
    _initialized = True


def get_session() -> Generator[Session]:
    init_db()
    with SessionLocal() as session:
        yield session

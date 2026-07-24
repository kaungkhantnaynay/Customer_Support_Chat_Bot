from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.models import Base


def _sync_database_url(database_url: str) -> str:
    return database_url.replace("sqlite+aiosqlite:///", "sqlite:///")


engine = create_engine(_sync_database_url(settings.database_url))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_initialized = False


def init_db() -> None:
    global _initialized
    if _initialized:
        return

    Base.metadata.create_all(bind=engine)
    _initialized = True


def get_session() -> Generator[Session]:
    init_db()
    with SessionLocal() as session:
        yield session

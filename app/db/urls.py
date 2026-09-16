from sqlalchemy.engine import URL, make_url


def sync_database_url(value: str) -> URL:
    url = make_url(value)
    if url.drivername == "sqlite+aiosqlite":
        return url.set(drivername="sqlite")
    if url.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
        return url.set(drivername="postgresql+psycopg")
    if url.drivername != "sqlite":
        raise ValueError("Use a SQLite or PostgreSQL psycopg database URL.")
    return url

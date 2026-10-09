"""Database engine and session handling.

Runs on SQLite locally and on Postgres when deployed — the only difference
is the `DATABASE_URL`, so the dialect is detected here rather than being
configured in two places.
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def _engine_kwargs(url: str) -> dict:
    """Connection settings that differ between SQLite and Postgres."""
    if url.startswith("sqlite"):
        return {
            # FastAPI serves requests from a thread pool, while SQLite
            # connections default to single-thread use.
            "connect_args": {"check_same_thread": False},
        }

    # On serverless the process may be frozen between requests, so a pooled
    # connection can be dead by the time it is reused. Check before handing
    # one out, and recycle well inside any provider idle timeout.
    return {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 1,
        "max_overflow": 2,
        "connect_args": {"connect_timeout": 10},
    }


def _normalise(url: str) -> str:
    """Accept the URLs hosting providers hand out.

    Neon, Supabase and Heroku all print `postgres://…`, which SQLAlchemy no
    longer recognises, and none of them mention the driver.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalise(settings.resolved_database_url)

engine = create_engine(DATABASE_URL, echo=False, **_engine_kwargs(DATABASE_URL))


def create_db_and_tables() -> None:
    # Importing models registers them on SQLModel.metadata before create_all.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

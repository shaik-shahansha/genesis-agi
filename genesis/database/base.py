"""Database base configuration and session management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from genesis.config import get_settings

# Create declarative base
Base = declarative_base()

# Global engine and session factory
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()

        # Determine database URL
        if settings.database_url.startswith("sqlite"):
            # For SQLite, ensure the path is absolute and directory exists
            db_path = settings.genesis_home / "genesis.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{db_path}"
        else:
            database_url = settings.database_url

        _engine = create_engine(
            database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )

        # Enable foreign keys for SQLite
        if "sqlite" in database_url:
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.query(MindRecord).all()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize the database (create all tables)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (dangerous!)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)

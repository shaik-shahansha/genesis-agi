"""Database base configuration and session management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from genesis.config import get_settings

logger = logging.getLogger(__name__)

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


def _reconcile_additive_columns(engine: Engine) -> list[str]:
    """Add columns the models declare but existing tables lack.

    `create_all` creates missing *tables* and never alters an existing one. That
    is fine until a model gains a column: on a fresh database the column exists,
    and on an existing one it silently does not.

    That gap is not hypothetical here. Adding `users.hashed_password` meant an
    existing install kept a `users` table without it, and every credential read
    failed with "no such column" — which, because authentication fails closed,
    presented as *login having stopped working* with nothing in the logs
    explaining why.

    So the app reconciles additive changes at startup, because it self-initialises
    its schema by default (`RUN_MIGRATIONS=false` in compose). Only additions are
    performed, and only when the column is nullable or defaulted, so the statement
    can never fail on existing rows. Everything else — a type change, a rename, a
    constraint, anything that needs data moved — is a real migration and is left
    to Alembic, with a warning naming it.

    Returns the columns added, for logging and for callers that want to assert.
    """
    inspector = inspect(engine)
    added: list[str] = []

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue

        present = {column["name"] for column in inspector.get_columns(table.name)}

        for column in table.columns:
            if column.name in present:
                continue

            safe = column.nullable or column.default is not None or column.server_default is not None
            if not safe:
                logger.warning(
                    "Column %s.%s is missing and is NOT NULL without a default. "
                    "This cannot be added automatically; apply the Alembic migration "
                    "for it (set RUN_MIGRATIONS=true, or run `alembic upgrade head`).",
                    table.name,
                    column.name,
                )
                continue

            statement = (
                f'ALTER TABLE "{table.name}" '
                f'ADD COLUMN "{column.name}" {column.type.compile(engine.dialect)}'
            )
            try:
                with engine.begin() as connection:
                    connection.execute(text(statement))
                added.append(f"{table.name}.{column.name}")
                logger.info("Added missing column %s.%s", table.name, column.name)
            except Exception as exc:  # noqa: BLE001 - never block startup on this
                logger.warning(
                    "Could not add %s.%s: %s. If this column is needed, apply the "
                    "Alembic migration (RUN_MIGRATIONS=true, or `alembic upgrade head`).",
                    table.name,
                    column.name,
                    exc,
                )

    return added


def init_db() -> None:
    """Initialize the database: create missing tables and add missing columns."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _reconcile_additive_columns(engine)



def drop_db() -> None:
    """Drop all tables (dangerous!)."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)

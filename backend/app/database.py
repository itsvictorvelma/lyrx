"""Database connection.

Alembic creates and changes the tables. Do not call Base.metadata.create_all.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import Pool


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str, poolclass: type[Pool] | None = None) -> Engine:
    options: dict[str, object] = {}
    if poolclass is not None:
        options["poolclass"] = poolclass
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            # ponytail: SQLite ignores foreign keys unless this is set on each connection.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def open_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    engine = make_engine(database_url)
    return engine, sessionmaker(bind=engine)

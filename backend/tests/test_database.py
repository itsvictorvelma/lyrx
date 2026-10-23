from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.database import make_engine
from app.main import create_app
from tests.test_app import settings

SONG_TABLES = {"tracks", "lyric_versions", "rights_records"}
FORBIDDEN_COLUMNS = {
    "active_line",
    "cue",
    "end_time",
    "offset",
    "start_time",
    "timestamp",
    "timestamps",
    "timing",
}


def migration_config(database_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def test_upgrade_creates_only_song_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "lyrx.db"
    command.upgrade(migration_config(database_path), "head")

    engine = make_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert SONG_TABLES <= tables
    assert tables - SONG_TABLES == {"alembic_version"}
    for table in SONG_TABLES:
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert columns.isdisjoint(FORBIDDEN_COLUMNS)
    engine.dispose()


def test_downgrade_removes_song_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "lyrx.db"
    config = migration_config(database_path)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = make_engine(f"sqlite:///{database_path}")
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert SONG_TABLES.isdisjoint(tables)


def test_health_does_not_create_database(tmp_path: Path) -> None:
    database_path = tmp_path / "lyrx.db"
    app = create_app(settings(database_url=f"sqlite:///{database_path}"))

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert not database_path.exists()

import os
from dataclasses import replace
from pathlib import Path

import pytest

from agent_suite.config import Settings
from agent_suite.storage import Database


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "suite.db"), os.getenv("TEST_DATABASE_URL", ""))
    if database.postgres:
        # TEST_DATABASE_URL must name an expendable test database.
        database.initialize()
        with database.connection(write=True) as conn:
            database.execute(
                conn, "TRUNCATE orders,quotes,products,stores,issues,bug_drafts CASCADE"
            )
    database.seed_demo()
    return database


@pytest.fixture
def settings(tmp_path, db):
    return Settings(
        mode="demo",
        database_path=db.path,
        database_url=db.url,
        workspace_root=Path(__file__).resolve().parents[1] / "examples",
        session_database_url=f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}",
    )


@pytest.fixture
def trusted_settings(settings):
    return replace(settings, review_test_mode="trusted")

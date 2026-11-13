"""Test setup: a real Postgres database (TEST_DATABASE_URL), migrated once and emptied before each test."""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg:///intake_test")

from collections.abc import Iterator  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.clock import get_now  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import create_app, get_transport  # noqa: E402
from tests.fakes import FakeTransport  # noqa: E402

BACKEND = Path(__file__).parent.parent
NOW = datetime(2026, 11, 13, 15, 30, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture(scope="session")
def migrated() -> None:
    with get_engine().begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def fake_model() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def client(migrated: None, clock: Clock, fake_model: FakeTransport) -> Iterator[TestClient]:
    with get_engine().begin() as connection:
        connection.execute(text("TRUNCATE intake_session, health_summary, intake_answer, llm_call RESTART IDENTITY"))
    app = create_app()
    app.dependency_overrides[get_now] = clock
    app.dependency_overrides[get_transport] = lambda: fake_model
    with TestClient(app) as test_client:
        yield test_client

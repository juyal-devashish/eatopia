from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import NOW, Clock
from tests.flow import _key


@pytest.mark.parametrize("given", ["postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db"])
def test_hosting_database_urls_get_the_psycopg_driver(given: str) -> None:
    settings = Settings(_env_file=None, database_url=given)  # type: ignore[call-arg]

    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_the_offline_stand_in_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="never production"):
        Settings(_env_file=None, environment="production", llm_transport="offline")  # type: ignore[call-arg]


def _create(client: TestClient, forwarded: str, key: str | None = None) -> int:
    response = client.post(
        "/sessions",
        json={"member_id": "a", "mode": "today", "client_key": key or _key()},
        headers={"X-Forwarded-For": forwarded},
    )
    return response.status_code


def test_one_client_can_start_20_sessions_an_hour(client: TestClient, clock: Clock) -> None:
    statuses = [_create(client, "203.0.113.9") for _ in range(21)]

    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429
    assert _create(client, "198.51.100.4") == 200
    clock.now = NOW + timedelta(hours=1, seconds=1)
    assert _create(client, "203.0.113.9") == 200


def test_a_forged_left_entry_does_not_dodge_the_limit(client: TestClient) -> None:
    for i in range(20):
        _create(client, f"10.0.0.{i}, 203.0.113.9")

    assert _create(client, "10.9.9.9, 203.0.113.9") == 429


def test_a_retried_create_is_never_limited(client: TestClient) -> None:
    for _ in range(20):
        _create(client, "203.0.113.9")

    key = _key()
    assert _create(client, "198.51.100.4", key) == 200
    assert _create(client, "203.0.113.9", key) == 200

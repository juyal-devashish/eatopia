from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import LlmSettings
from app.db import get_engine
from tests.conftest import NOW, Clock
from tests.fakes import FakeTransport, matches, message
from tests.flow import _key, _start

CAP = LlmSettings().session_cap


def _match(client: TestClient, session_id: str, words: str, key: str | None = None) -> Any:
    return client.post(f"/sessions/{session_id}/conditions/match", json={"text": words, "request_key": key or _key()})


def test_match_returns_labelled_suggestions(client: TestClient, fake_model: FakeTransport) -> None:
    state = _start(client, "a", "health_first")

    body = _match(client, state["id"], "my sugar is borderline and I get heartburn").json()

    assert body["status"] == "ok"
    assert [m["label"] for m in body["matches"]] == ["Prediabetes", "Acid reflux or GERD"]
    assert body["show_full_list"] is False
    assert len(fake_model.requests) == 1


def test_retried_match_calls_the_model_once(client: TestClient, fake_model: FakeTransport) -> None:
    state = _start(client, "a", "health_first")

    first = _match(client, state["id"], "heartburn", key="match-retry-1").json()
    second = _match(client, state["id"], "heartburn", key="match-retry-1").json()

    assert first == second
    assert len(fake_model.requests) == 1


def test_match_in_progress_asks_the_client_to_retry(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO llm_call (session_id, purpose, request_key, status, model, created_at) "
                "VALUES (:id, 'condition_match', 'match-pending-1', 'pending', 'm', now())"
            ),
            {"id": state["id"]},
        )

    assert _match(client, state["id"], "heartburn", key="match-pending-1").status_code == 409


def test_session_cap_falls_back_to_the_full_list(client: TestClient, fake_model: FakeTransport) -> None:
    state = _start(client, "a", "health_first")
    for _ in range(CAP):
        assert _match(client, state["id"], "heartburn").json()["status"] == "ok"

    body = _match(client, state["id"], "heartburn").json()

    assert body["status"] == "capped"
    assert body["show_full_list"] is True
    assert len(fake_model.requests) == CAP


def test_daily_cap_applies_across_sessions(client: TestClient, fake_model: FakeTransport, monkeypatch: Any) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings().llm, "daily_cap", 2)
    first, second = _start(client, "a", "today"), _start(client, "b", "today")
    _match(client, first["id"], "heartburn")
    _match(client, first["id"], "heartburn")

    assert _match(client, second["id"], "heartburn").json()["status"] == "capped"


def test_daily_cap_resets_the_next_day(client: TestClient, clock: Clock, monkeypatch: Any) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings().llm, "daily_cap", 1)
    _match(client, _start(client, "a", "today")["id"], "heartburn")
    clock.now = NOW + timedelta(days=1)

    assert _match(client, _start(client, "b", "today")["id"], "heartburn").json()["status"] == "ok"


def test_refusal_is_recorded_and_falls_back(client: TestClient, fake_model: FakeTransport) -> None:
    async def refuse(request: dict[str, Any]) -> dict[str, Any]:
        return message("", stop_reason="refusal")

    fake_model.responder = refuse
    state = _start(client, "a", "health_first")

    body = _match(client, state["id"], "heartburn").json()
    log = client.get(f"/sessions/{state['id']}/egress").json()

    assert body["status"] == "refused"
    assert body["show_full_list"] is True
    assert log[0]["status"] == "refused"


def test_empty_or_long_text_is_rejected(client: TestClient, fake_model: FakeTransport) -> None:
    state = _start(client, "a", "health_first")

    assert _match(client, state["id"], "   ").status_code == 422
    assert _match(client, state["id"], "x" * 301).status_code == 422
    assert fake_model.requests == []


def test_egress_log_shows_exactly_what_was_sent(client: TestClient, fake_model: FakeTransport) -> None:
    state = _start(client, "a", "health_first")
    _match(client, state["id"], "email me at sam@example.com about my gout")

    log = client.get(f"/sessions/{state['id']}/egress").json()

    assert log[0]["request"] == fake_model.requests[0]
    assert "sam@example.com" not in str(log[0]["request"])
    assert "[removed]" in log[0]["request"]["messages"][0]["content"]


def test_capped_calls_are_logged_with_nothing_sent(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    for _ in range(CAP + 1):
        _match(client, state["id"], "heartburn")

    log = client.get(f"/sessions/{state['id']}/egress").json()

    assert log[-1]["status"] == "capped"
    assert log[-1]["request"] is None


def _match_option(client: TestClient, session_id: str, screen_id: str, words: str) -> Any:
    return client.post(f"/sessions/{session_id}/screens/{screen_id}/match", json={"text": words, "request_key": _key()})


def test_something_else_maps_onto_the_questions_options(client: TestClient, fake_model: FakeTransport) -> None:
    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        return matches(("dairy", "high"))

    fake_model.responder = respond
    state = _start(client, "a", "today")

    body = _match_option(client, state["id"], "allergies", "milk makes me bloated").json()
    sent = fake_model.requests[0]
    offered = sent["output_config"]["format"]["schema"]["properties"]["matches"]["items"]["properties"]["id"]["enum"]

    assert [m["label"] for m in body["matches"]] == ["Dairy or lactose"]
    assert "other" not in offered
    assert "<question>Any food allergies or intolerances?</question>" in sent["messages"][0]["content"]


def test_option_matching_needs_a_free_text_question(client: TestClient) -> None:
    state = _start(client, "a", "today")

    assert _match_option(client, state["id"], "meals_per_day", "five").status_code == 404
    assert _match_option(client, state["id"], "no_such_screen", "five").status_code == 404


def test_option_and_condition_calls_share_the_session_cap(client: TestClient) -> None:
    state = _start(client, "a", "today")
    for _ in range(CAP):
        _match(client, state["id"], "heartburn")

    assert _match_option(client, state["id"], "allergies", "milk").json()["status"] == "capped"

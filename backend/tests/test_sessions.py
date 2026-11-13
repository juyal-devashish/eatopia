from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.db import IntakeAnswer, IntakeSession, get_engine
from app.health.members import load_member
from app.health.models import resolve
from app.health.summary import build_summary
from app.questions import load_schema
from tests.conftest import NOW, Clock

SCREENS = {screen.id: screen for screen in load_schema().screens}
_keys = iter(range(10_000_000))


def _key() -> str:
    return f"key-{next(_keys):08d}"


def _start(client: TestClient, member: str, mode: str) -> dict[str, Any]:
    response = client.post("/sessions", json={"member_id": member, "mode": mode, "client_key": _key()})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _answer(
    client: TestClient,
    state: dict[str, Any],
    screen_id: str,
    value: Any,
    key: str | None = None,
    taps: int = 1,
) -> dict[str, Any]:
    response = client.post(
        f"/sessions/{state['id']}/answers",
        json={"screen_id": screen_id, "value": value, "idempotency_key": key or _key(), "taps": taps},
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _default(state: dict[str, Any], screen_id: str) -> Any:
    """A valid answer for any screen: the suggestion where there is one, else the first option."""
    screen = SCREENS[screen_id]
    suggestion = state["suggestions"].get(screen_id)
    if suggestion and suggestion["status"] != "ask":
        return suggestion["value"]
    match screen.kind:
        case "single_choice":
            return screen.options[0].id
        case "multi_choice":
            return [next(o.id for o in screen.options if not o.free_text)]
        case "date":
            return "1990-01-01"
        case "height":
            return {"cm": 170}
        case "weight":
            return {"kg": 70}
        case "text":
            return "None"
        case "condition_picker":
            return "none"
        case "health_permission":
            return {"granted": True}
        case "health_review":
            return {"rows": {row: state["suggestions"][row]["value"] for row in state["review_rows"]}}
        case _:
            return {"seen": True}


def _run_to(
    client: TestClient, state: dict[str, Any], stop_at: str | None = None
) -> tuple[dict[str, Any], list[str]]:
    visited = []
    while state["next_screen_id"] not in (None, stop_at):
        screen_id = state["next_screen_id"]
        visited.append(screen_id)
        state = _answer(client, state, screen_id, _default(state, screen_id))
    return state, visited


def _answer_count(session_id: str) -> int:
    with get_engine().connect() as connection:
        count = connection.scalar(
            select(func.count()).select_from(IntakeAnswer).where(IntakeAnswer.session_id == session_id)
        )
    return int(count or 0)


# Sessions


def test_new_session_starts_at_the_first_screen(client: TestClient) -> None:
    state = _start(client, "a", "health_first")

    assert state["next_screen_id"] == "main_goal"
    assert state["suggestions"] == {}
    assert not state["finished"]


def test_retried_create_returns_the_same_session(client: TestClient) -> None:
    body = {"member_id": "a", "mode": "today", "client_key": "retry-create-1"}

    first = client.post("/sessions", json=body).json()
    second = client.post("/sessions", json=body).json()

    assert first["id"] == second["id"]


def test_reused_client_key_for_another_session_is_rejected(client: TestClient) -> None:
    client.post("/sessions", json={"member_id": "a", "mode": "today", "client_key": "reused-key-1"})

    response = client.post(
        "/sessions", json={"member_id": "a", "mode": "health_first", "client_key": "reused-key-1"}
    )

    assert response.status_code == 409


def test_unknown_member_is_rejected(client: TestClient) -> None:
    response = client.post("/sessions", json={"member_id": "z", "mode": "today", "client_key": _key()})

    assert response.status_code == 422


def test_session_resumes_where_it_left_off(client: TestClient) -> None:
    state = _start(client, "a", "today")
    state, _ = _run_to(client, state, stop_at="height")

    resumed = client.get(f"/sessions/{state['id']}").json()

    assert resumed["next_screen_id"] == "height"
    assert set(resumed["answers"]) == {
        "main_goal",
        "dietitian_note",
        "gender_identity",
        "sex_at_birth",
        "date_of_birth",
    }


def test_sessions_expire_after_24_hours(client: TestClient, clock: Clock) -> None:
    state = _start(client, "a", "today")
    clock.now = NOW + timedelta(hours=25)

    assert client.get(f"/sessions/{state['id']}").status_code == 404


def test_creating_a_session_deletes_expired_ones(client: TestClient, clock: Clock) -> None:
    _start(client, "a", "today")
    clock.now = NOW + timedelta(hours=25)
    _start(client, "b", "today")

    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(IntakeSession)) == 1


# Answers: saved once, replaced on Back


def test_retried_answer_is_saved_once(client: TestClient) -> None:
    state = _start(client, "a", "today")

    first = _answer(client, state, "main_goal", "energy", key="same-key-1", taps=2)
    second = _answer(client, state, "main_goal", "energy", key="same-key-1", taps=2)

    assert _answer_count(state["id"]) == 1
    assert first == second
    assert second["tap_count"] == 2


def test_retry_with_the_same_key_does_not_overwrite(client: TestClient) -> None:
    state = _start(client, "a", "today")
    _answer(client, state, "main_goal", "energy", key="same-key-2")

    after = _answer(client, state, "main_goal", "digestion", key="same-key-2")

    assert after["answers"]["main_goal"]["value"] == "energy"


def test_new_key_replaces_the_answer_after_back(client: TestClient) -> None:
    state = _start(client, "a", "today")
    _answer(client, state, "main_goal", "energy")

    after = _answer(client, state, "main_goal", "digestion")

    assert after["answers"]["main_goal"]["value"] == "digestion"
    assert _answer_count(state["id"]) == 1


@pytest.mark.parametrize(
    ("screen_id", "value"),
    [
        ("main_goal", "fly"),
        ("main_goal", {"option": "energy", "text": "x"}),
        ("allergies", ["none", "dairy"]),
        ("allergies", []),
        ("weight", {"kg": 900}),
        ("height", {"cm": True}),
        ("date_of_birth", "13/11/1990"),
        ("gender_identity", None),
        ("health_concern", {"condition_id": "made_up"}),
    ],
)
def test_invalid_answers_are_rejected(client: TestClient, screen_id: str, value: Any) -> None:
    state = _start(client, "a", "today")

    response = client.post(
        f"/sessions/{state['id']}/answers",
        json={"screen_id": screen_id, "value": value, "idempotency_key": _key()},
    )

    assert response.status_code == 422


def test_free_text_option_and_skips_are_accepted(client: TestClient) -> None:
    state = _start(client, "a", "today")

    state = _answer(client, state, "main_goal", {"option": "other", "text": "Sleep better"})
    state = _answer(client, state, "weight", None)

    assert state["answers"]["weight"] == {"value": None, "source": "member"}


# Health first


def test_health_first_member_a_reviews_five_facts(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, visited = _run_to(client, state, stop_at="health_review")

    assert visited == ["main_goal", "dietitian_note", "health_benefit", "health_permission_early"]
    assert state["review_rows"] == ["sex_at_birth", "date_of_birth", "height", "weight", "steps"]
    assert len(state["suggestions"]) == 7


def test_review_card_records_confirmed_and_changed_answers(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")
    rows = {row: state["suggestions"][row]["value"] for row in state["review_rows"]}
    rows["weight"] = {"kg": 75.0}

    state = _answer(client, state, "health_review", {"rows": rows})

    assert state["answers"]["height"]["source"] == "health_confirmed"
    assert state["answers"]["weight"]["source"] == "health_changed"
    assert state["next_screen_id"] == "gender_identity"


def test_review_card_must_include_exactly_its_rows(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")

    response = client.post(
        f"/sessions/{state['id']}/answers",
        json={
            "screen_id": "health_review",
            "value": {"rows": {"height": {"cm": 170}}},
            "idempotency_key": _key(),
        },
    )

    assert response.status_code == 422


def test_reviewed_facts_are_not_asked_again(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")
    state = _answer(client, state, "health_review", _default(state, "health_review"))
    state = _answer(client, state, "gender_identity", "woman")

    assert state["next_screen_id"] == "weight_goal"


def test_estimate_picked_as_suggested_is_marked_from_health(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="exercise_frequency")

    assert state["suggestions"]["exercise_frequency"]["kind"] == "estimate"
    state = _answer(client, state, "exercise_frequency", "d5_6")
    assert state["answers"]["exercise_frequency"]["source"] == "health_confirmed"


def test_member_b_reviews_only_usable_facts(client: TestClient) -> None:
    state = _start(client, "b", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")

    assert state["review_rows"] == ["date_of_birth", "height", "steps"]


def test_member_c_skips_the_empty_review_card(client: TestClient) -> None:
    state = _start(client, "c", "health_first")
    state, visited = _run_to(client, state, stop_at="sex_at_birth")

    assert "health_review" not in visited
    assert state["review_rows"] == []


def test_denied_permission_asks_everything(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_permission_early")

    state = _answer(client, state, "health_permission_early", {"granted": False})

    assert state["suggestions"] == {}
    assert state["next_screen_id"] == "gender_identity"


def test_todays_order_makes_no_suggestions(client: TestClient) -> None:
    state = _start(client, "a", "today")
    state, visited = _run_to(client, state)

    assert state["finished"]
    assert state["suggestions"] == {}
    assert "health_permission_late" in visited
    assert {a["source"] for a in state["answers"].values()} == {"member"}


def test_review_card_is_not_part_of_todays_order(client: TestClient) -> None:
    state = _start(client, "a", "today")

    response = client.post(
        f"/sessions/{state['id']}/answers",
        json={"screen_id": "health_review", "value": {"rows": {}}, "idempotency_key": _key()},
    )

    assert response.status_code == 422


def test_member_a_sees_three_fewer_screens_in_health_first(client: TestClient) -> None:
    _, today = _run_to(client, _start(client, "a", "today"))
    _, health_first = _run_to(client, _start(client, "a", "health_first"))

    assert len(today) == 25
    assert len(health_first) == 22


# The HealthKit contract


def test_iphone_summary_drives_the_suggestions(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    summary = build_summary(resolve(load_member("a"), NOW), NOW)
    edited = summary.model_copy(update={"biological_sex": "male"})

    response = client.post(f"/sessions/{state['id']}/health-summary", json=edited.model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["suggestions"]["sex_at_birth"]["value"] == "male"


def test_stored_summary_must_be_device_data(client: TestClient) -> None:
    state = _start(client, "a", "health_first")

    with pytest.raises(IntegrityError), get_engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO health_summary (session_id, schema_version, data, data_class, received_at) "
                "VALUES (:id, 1, '{}', 'member', now())"
            ),
            {"id": state["id"]},
        )


def test_withdrawing_access_after_back_forgets_health_data(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")
    assert state["suggestions"]

    state = _answer(client, state, "health_permission_early", {"granted": False})

    assert state["suggestions"] == {}
    assert state["review_rows"] == []

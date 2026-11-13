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
from tests.conftest import NOW, Clock
from tests.flow import _answer, _default, _key, _run_to, _start


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

    response = client.post("/sessions", json={"member_id": "a", "mode": "health_first", "client_key": "reused-key-1"})

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


def test_health_first_state_includes_the_members_own_summary(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")

    assert state["health_summary"]["latest_weight"]["value"] == 73.417
    assert len(state["health_summary"]["daily_steps_30d"]) == 30


def test_todays_order_state_has_no_summary(client: TestClient) -> None:
    state = _start(client, "a", "today")
    state, _ = _run_to(client, state)

    assert state["health_summary"] is None


def test_stats_count_screens_seen_and_answers_from_health(client: TestClient) -> None:
    _, _ = _run_to(client, _start(client, "a", "today"))
    today, _ = _run_to(client, _start(client, "a", "today"))
    health_first, _ = _run_to(client, _start(client, "a", "health_first"))

    assert today["stats"] == {
        "screens_seen": 25,
        "filled_from_health": 0,
        "changed_from_health": 0,
        "estimates_taken": 0,
    }
    assert health_first["stats"] == {
        "screens_seen": 22,
        "filled_from_health": 5,
        "changed_from_health": 0,
        "estimates_taken": 2,
    }


def test_stats_count_a_changed_row(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="health_review")
    rows = {row: state["suggestions"][row]["value"] for row in state["review_rows"]}
    rows["steps"] = "s12000_plus"

    state = _answer(client, state, "health_review", {"rows": rows})

    assert state["stats"]["filled_from_health"] == 4
    assert state["stats"]["changed_from_health"] == 1


def test_picking_something_other_than_an_estimate_is_the_members_own_answer(client: TestClient) -> None:
    state = _start(client, "a", "health_first")
    state, _ = _run_to(client, state, stop_at="exercise_frequency")

    state = _answer(client, state, "exercise_frequency", "d1_2")

    assert state["answers"]["exercise_frequency"]["source"] == "member"
    assert state["stats"]["changed_from_health"] == 0

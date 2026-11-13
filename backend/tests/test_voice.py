"""Voice screens: what the member says becomes answers they confirm on the same screen."""

import json
from typing import Any

from fastapi.testclient import TestClient

from app.health.members import MEMBER_IDS, load_member
from app.offline_model import OfflineTransport
from app.voice import load_scripts
from tests.fakes import FakeTransport, message
from tests.flow import _answer, _default, _key, _run_to, _start

SAID = "I want more energy, my doctor mentioned prediabetes, my schedule keeps changing, I eat three times a day."
HEARD = {
    "main_goal": "energy",
    "weight_goal": None,
    "health_concern": "prediabetes",
    "eating_barriers": ["schedule"],
    "meals_per_day": "three",
}


def _at_voice(client: TestClient) -> dict[str, Any]:
    state, _ = _run_to(client, _start(client, "a", "health_first"), stop_at="voice_goals")
    return state


def _extract(client: TestClient, state: dict[str, Any], text: str = SAID, key: str | None = None) -> Any:
    return client.post(
        f"/sessions/{state['id']}/screens/voice_goals/extract", json={"text": text, "request_key": key or _key()}
    )


def _replies(payload: dict[str, Any]) -> Any:
    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        return message(json.dumps(payload))

    return respond


def test_extraction_fills_answers_in_the_endpoints_shapes(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _replies(HEARD)
    state = _at_voice(client)

    body = _extract(client, state).json()

    assert body["status"] == "ok"
    assert body["answers"] == HEARD | {"health_concern": {"condition_id": "prediabetes"}}


def test_the_request_holds_only_the_members_words_and_our_lists(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _replies(HEARD)
    _extract(client, _at_voice(client))

    request = fake_model.requests[0]
    content = request["messages"][0]["content"]
    assert f"<member_text>{SAID}</member_text>" in content
    assert '<question id="main_goal" answer="one option">' in content
    assert "- energy: More energy" in content
    assert "Something else" not in content  # free-text options stay out of the lists
    schema = request["output_config"]["format"]["schema"]
    assert set(schema["required"]) == set(HEARD)
    assert schema["properties"]["main_goal"]["anyOf"][1] == {"type": "null"}


def test_own_words_the_member_never_said_are_dropped(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _replies(
        {
            "who_cooks": "me",
            "weeknight_time": None,
            "food_budget": None,
            "eating_out": None,
            "medications": "metformin twice a day",
            "anything_else": "vitamin D",
        }
    )
    state, _ = _run_to(client, _start(client, "a", "health_first"), stop_at="voice_kitchen")

    body = client.post(
        f"/sessions/{state['id']}/screens/voice_kitchen/extract",
        json={"text": "I cook. I take Vitamin  D every morning.", "request_key": _key()},
    ).json()

    assert body["answers"]["who_cooks"] == "me"
    assert body["answers"]["medications"] is None
    assert body["answers"]["anything_else"] == "vitamin D"


def test_an_answer_outside_our_lists_fails_safely(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _replies(HEARD | {"main_goal": "world_peace"})

    body = _extract(client, _at_voice(client)).json()

    assert body["status"] == "parse_failed"
    assert set(body["answers"].values()) == {None}


def test_a_retried_extraction_calls_the_model_once(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _replies(HEARD)
    state = _at_voice(client)

    first = _extract(client, state, key="voice-retry-1").json()
    second = _extract(client, state, key="voice-retry-1").json()

    assert first == second
    assert len(fake_model.requests) == 1


def test_only_voice_screens_take_a_spoken_answer(client: TestClient) -> None:
    state = _at_voice(client)

    response = client.post(
        f"/sessions/{state['id']}/screens/main_goal/extract", json={"text": SAID, "request_key": _key()}
    )

    assert response.status_code == 404


def test_confirmed_answers_are_marked_as_heard_and_edits_as_the_members(
    client: TestClient, fake_model: FakeTransport
) -> None:
    fake_model.responder = _replies(HEARD)
    state = _at_voice(client)
    heard = _extract(client, state).json()["answers"]
    rows = heard | {"weight_goal": "maintain", "meals_per_day": "two"}

    state = _answer(client, state, "voice_goals", {"rows": rows})

    assert state["answers"]["main_goal"]["source"] == "voice_confirmed"
    assert state["answers"]["health_concern"]["source"] == "voice_confirmed"
    assert state["answers"]["weight_goal"]["source"] == "member"  # not mentioned, tapped
    assert state["answers"]["meals_per_day"]["source"] == "member"  # heard, then changed
    assert state["stats"]["filled_from_voice"] == 3


def test_the_offline_stand_in_fills_what_it_clearly_heard(client: TestClient) -> None:
    from app.main import get_transport

    client.app.dependency_overrides[get_transport] = OfflineTransport  # type: ignore[attr-defined]
    state = _at_voice(client)

    body = _extract(client, state, text=load_scripts("a")["voice_goals"]).json()

    assert body["answers"]["main_goal"] == "energy"
    assert body["answers"]["health_concern"] == {"condition_id": "prediabetes"}
    assert body["answers"]["meals_per_day"] == "three"


def test_member_a_has_a_script_for_every_voice_screen(client: TestClient) -> None:
    state = _at_voice(client)

    assert set(state["voice_scripts"]) == {"voice_goals", "voice_food", "voice_kitchen"}
    assert _start(client, "a", "today")["voice_scripts"] == {}


def test_voice_scripts_hold_no_health_marker() -> None:
    for member_id in MEMBER_IDS:
        said = " ".join(load_scripts(member_id).values())
        assert not [v for v in load_member(member_id).canary_values if v in said]


def test_flow_default_still_finishes_without_extraction(client: TestClient) -> None:
    state = _at_voice(client)
    state = _answer(client, state, "voice_goals", _default(state, "voice_goals"))

    assert state["next_screen_id"] == "voice_food"

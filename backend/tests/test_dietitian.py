import json
from typing import Any

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.dietitian import NOT_PROVIDED, fill_placeholders, member_answers, placeholders
from app.questions import load_schema
from tests.fakes import FakeTransport, message
from tests.flow import _key, _run_to, _start

SCHEMA = load_schema()
CATALOG = load_catalog()


def _summary_reply(text: str) -> Any:
    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        return message(json.dumps({"summary": text}))

    return respond


def test_member_answers_leave_out_health_linked_and_scrub_free_text() -> None:
    answers = {
        "main_goal": "energy",
        "weight": {"kg": 73.4},
        "steps": "s9000_11999",
        "exercise_frequency": "d5_6",
        "medications": "metformin, email me at sam@example.com",
        "dietitian_note": {"seen": True},
    }

    items = dict(member_answers(SCHEMA, answers, CATALOG).items)

    assert items == {
        "What would you most like to work on first?": "More energy",
        "Do you take any medications or supplements?": "metformin, email me at [removed]",
    }


def test_placeholders_are_filled_from_answers() -> None:
    answers = {"weight": {"kg": 73.4}, "height": None, "steps": "s9000_11999"}

    text, used = fill_placeholders(
        "Weighs {{weight}}, height {{height}}, walks {{ steps }}, and {{password}}.", SCHEMA, answers, CATALOG
    )

    assert text == f"Weighs 162 lb (73.4 kg), height {NOT_PROVIDED}, walks 9,000 to 11,999, and {NOT_PROVIDED}."
    assert used == ["weight", "height", "steps"]


def test_placeholders_are_the_health_linked_questions() -> None:
    assert set(placeholders(SCHEMA)) == {
        "sex_at_birth",
        "date_of_birth",
        "height",
        "weight",
        "steps",
        "exercise_frequency",
        "activity_level",
    }


def test_summary_endpoint_fills_health_values_after_the_model(client: TestClient, fake_model: FakeTransport) -> None:
    fake_model.responder = _summary_reply("Wants more energy. Weight {{weight}}; about {{steps}} steps a day.")
    state, _ = _run_to(client, _start(client, "a", "health_first"))
    key = _key()

    body = client.post(f"/sessions/{state['id']}/summary", json={"request_key": key}).json()
    again = client.post(f"/sessions/{state['id']}/summary", json={"request_key": key}).json()

    assert body["written_by_model"] is True
    assert body["writer"] == "claude-sonnet-5-5"
    assert body["text"] == "Wants more energy. Weight 162 lb (73.4 kg); about 9,000 to 11,999 steps a day."
    assert body["health_values_filled"] == ["weight", "steps"]
    assert again == body
    assert len(fake_model.requests) == 1
    assert "73.4" not in json.dumps(fake_model.requests[0])


def test_summary_falls_back_to_a_template_when_refused(client: TestClient, fake_model: FakeTransport) -> None:
    async def refuse(request: dict[str, Any]) -> dict[str, Any]:
        return message("", stop_reason="refusal")

    fake_model.responder = refuse
    state, _ = _run_to(client, _start(client, "b", "today"))

    body = client.post(f"/sessions/{state['id']}/summary", json={"request_key": _key()}).json()

    assert body["status"] == "refused"
    assert body["written_by_model"] is False
    assert "Every answer is listed below" in body["text"]

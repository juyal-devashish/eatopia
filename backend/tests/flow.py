"""Helpers that drive an intake session through the API, as the web app would."""

from typing import Any

from fastapi.testclient import TestClient

from app.questions import load_schema

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


def _run_to(client: TestClient, state: dict[str, Any], stop_at: str | None = None) -> tuple[dict[str, Any], list[str]]:
    visited = []
    while state["next_screen_id"] not in (None, stop_at):
        screen_id = state["next_screen_id"]
        visited.append(screen_id)
        state = _answer(client, state, screen_id, _default(state, screen_id))
    return state, visited

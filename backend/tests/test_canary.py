"""The privacy test: no Health value ever reaches the model.

Each synthetic member carries unique marker values (for example 73.417 kg). We run every flow to the end, call
every model-facing endpoint along the way, and check that no marker, and no value derived from the member's
Health data, appears in anything sent to the model or stored as sent.
"""

import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import LlmCall, get_engine
from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId
from tests.fakes import FakeTransport
from tests.flow import _answer, _default, _key, _start

FREE_TEXT = "my sugar runs high and I get heartburn after dinner"


def _health_strings(member_id: MemberId, suggestions: dict[str, Any]) -> set[str]:
    """Strings that would show Health data leaking: the markers, plus every value and number the rules derived."""
    strings = set(load_member(member_id).canary_values)
    for result in suggestions.values():
        value = result["value"]
        if isinstance(value, dict):
            strings |= {str(v) for v in value.values()}
        elif isinstance(value, str) and re.search(r"\d", value):
            strings.add(value)
        strings |= set(re.findall(r"\d[\d,]{2,}", result["evidence"]))
    return strings


def _run_with_model_calls(client: TestClient, member_id: MemberId, mode: str) -> dict[str, Any]:
    """Finish a whole flow, calling every model-facing endpoint on the way, as a member could."""
    state = _start(client, member_id, mode)
    suggestions: dict[str, Any] = {}
    while state["next_screen_id"] is not None:
        screen_id = state["next_screen_id"]
        if screen_id == "health_concern":
            client.post(f"/sessions/{state['id']}/conditions/match", json={"text": FREE_TEXT, "request_key": _key()})
        if screen_id in ("allergies", "eating_barriers", "diet_pattern"):
            client.post(
                f"/sessions/{state['id']}/screens/{screen_id}/match",
                json={"text": "dairy upsets me and I am often too busy", "request_key": _key()},
            )
        suggestions |= state["suggestions"]
        state = _answer(client, state, screen_id, _default(state, screen_id))
    client.post(f"/sessions/{state['id']}/summary", json={"request_key": _key()})
    state["all_suggestions"] = suggestions | state["suggestions"]
    return state


@pytest.mark.parametrize("member_id", MEMBER_IDS)
@pytest.mark.parametrize("mode", ["health_first", "today"])
def test_no_health_value_reaches_the_model(
    client: TestClient, fake_model: FakeTransport, member_id: MemberId, mode: str
) -> None:
    state = _run_with_model_calls(client, member_id, mode)
    with get_engine().connect() as connection:
        stored = [row.request for row in connection.execute(select(LlmCall.request))]

    sent = json.dumps(fake_model.requests) + json.dumps(stored)
    health = _health_strings(member_id, state["all_suggestions"])

    assert fake_model.requests, "the flow should have called the model"
    assert state["finished"]
    leaked = sorted(s for s in health if s in sent)
    assert leaked == []


def test_markers_exist_where_the_test_needs_them() -> None:
    """Guard against the canary test passing because there is nothing to look for."""
    assert load_member("a").canary_values
    assert load_member("b").canary_values

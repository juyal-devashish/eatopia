import ast
import asyncio
import inspect
import typing
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest

from app import claude_client
from app.catalog import load_catalog
from app.claude_client import (
    REMOVED,
    CatalogRef,
    InvalidMemberText,
    MemberText,
    build_match_request,
    call_model,
    parse_match,
)
from app.config import LlmSettings
from tests.fakes import FakeTransport, matches, message

SETTINGS = LlmSettings()
CATALOG = CatalogRef.from_catalog(load_catalog())
FORBIDDEN_TYPES = ("HealthSummaryV1", "MemberHealthData", "QuantitySample", "Measurement", "RuleResult", "IntakeAnswer")
FORBIDDEN_IMPORTS = ("app.health", "app.rules", "app.intake", "app.db", "app.egress")


def _run(transport: FakeTransport) -> claude_client.Outcome:
    request = build_match_request(MemberText.from_member("borderline sugar", 300), CATALOG, SETTINGS)
    return asyncio.run(call_model(transport, request, CATALOG, SETTINGS))


# The firewall, structurally


def test_no_public_function_accepts_health_data() -> None:
    for name, obj in vars(claude_client).items():
        if name.startswith("_") or not inspect.isfunction(obj) or obj.__module__ != claude_client.__name__:
            continue
        for hint in typing.get_type_hints(obj).values():
            assert not any(forbidden in str(hint) for forbidden in FORBIDDEN_TYPES), name


def test_client_module_does_not_import_health_or_answers() -> None:
    tree = ast.parse(Path(claude_client.__file__).read_text())
    imported = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}

    assert not [m for m in imported if m.startswith(FORBIDDEN_IMPORTS)]


# Member text


@pytest.mark.parametrize(
    "raw",
    [
        "email me at sam.lee@example.com",
        "call +1 (734) 555-0199 please",
        "see https://example.com/me",
        "born 12/05/1991",
        "my member number is 4412 8890 1234",
    ],
)
def test_identifiers_are_removed(raw: str) -> None:
    text = MemberText.from_member(raw, 300)

    assert REMOVED in text.text
    assert text.removed >= 1


def test_ordinary_text_is_kept() -> None:
    text = MemberText.from_member("  heartburn after dinner,\n2 or 3 times a week ", 300)

    assert text.text == "heartburn after dinner, 2 or 3 times a week"
    assert text.removed == 0


@pytest.mark.parametrize("raw", ["", "   ", "x" * 301])
def test_empty_or_long_text_is_rejected(raw: str) -> None:
    with pytest.raises(InvalidMemberText):
        MemberText.from_member(raw, 300)


# Request and parsing


def test_request_limits_answers_to_catalog_ids() -> None:
    request = build_match_request(MemberText.from_member("heartburn", 300), CATALOG, SETTINGS)
    schema = request["output_config"]["format"]["schema"]

    assert schema["properties"]["matches"]["items"]["properties"]["condition_id"]["enum"] == CATALOG.ids()
    assert request["output_config"]["effort"] == "low"
    assert request["model"] == "claude-opus-5-5"
    assert request["fallbacks"] == "default"
    assert "<member_text>heartburn</member_text>" in request["messages"][0]["content"]


def test_parse_keeps_three_unique_matches() -> None:
    response = matches(("gout", "high"), ("gout", "low"), ("anemia", "low"), ("migraine", "low"), ("obesity", "low"))

    assert parse_match(response, CATALOG) == {
        "matches": [
            {"condition_id": "gout", "confidence": "high"},
            {"condition_id": "anemia", "confidence": "low"},
            {"condition_id": "migraine", "confidence": "low"},
        ]
    }


# Outcomes: every failure is recorded, never dropped


def test_ok_outcome() -> None:
    outcome = _run(FakeTransport())

    assert outcome.status == "ok"
    assert outcome.result is not None
    assert outcome.input_tokens == 600


@pytest.mark.parametrize(
    ("response", "status"),
    [
        (message("", stop_reason="refusal"), "refused"),
        (message('{"matches": [', stop_reason="max_tokens"), "parse_failed"),
        (message("not json"), "parse_failed"),
        (matches(("made_up", "high")), "parse_failed"),
    ],
)
def test_failed_outcomes(response: dict[str, Any], status: str) -> None:
    fake = FakeTransport()

    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        return response

    fake.responder = respond

    assert _run(fake).status == status


def test_timeout_outcome() -> None:
    fake = FakeTransport()

    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError

    fake.responder = respond

    assert _run(fake).status == "timeout"


def test_api_error_outcome() -> None:
    fake = FakeTransport()

    async def respond(request: dict[str, Any]) -> dict[str, Any]:
        raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))

    fake.responder = respond

    assert _run(fake).status == "error"

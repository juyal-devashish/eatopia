import asyncio

from app.catalog import load_catalog
from app.claude_client import CatalogRef, MemberText, build_match_request, build_option_request, call_model
from app.config import LlmSettings
from app.offline_model import OFFLINE_MODEL, OfflineTransport

SETTINGS = LlmSettings()


def test_offline_matcher_answers_condition_requests() -> None:
    catalog = CatalogRef.from_catalog(load_catalog())
    request = build_match_request(MemberText.from_member("my kidney stones are back", 300), catalog, SETTINGS)

    outcome = asyncio.run(call_model(OfflineTransport(), request, catalog, SETTINGS))

    assert outcome.status == "ok"
    assert outcome.result == {
        "matches": [
            {"id": "chronic_kidney_disease", "confidence": "medium"},
            {"id": "kidney_stones", "confidence": "medium"},
        ]
    }
    assert outcome.response is not None and outcome.response["model"] == OFFLINE_MODEL


def test_offline_matcher_answers_option_requests_and_can_find_nothing() -> None:
    options = CatalogRef(items=(("dairy", "Dairy or lactose"), ("gluten", "Gluten")))
    hit = build_option_request(MemberText.from_member("lactose upsets me", 300), "Allergies?", options, SETTINGS)
    miss = build_option_request(MemberText.from_member("nothing really", 300), "Allergies?", options, SETTINGS)

    assert asyncio.run(call_model(OfflineTransport(), hit, options, SETTINGS)).result == {
        "matches": [{"id": "dairy", "confidence": "medium"}]
    }
    assert asyncio.run(call_model(OfflineTransport(), miss, options, SETTINGS)).result == {"matches": []}


def test_offline_matcher_writes_a_labelled_summary() -> None:
    from app.claude_client import MemberAnswers, build_summary_request, parse_summary

    request = build_summary_request(MemberAnswers(items=(("Goal?", "More energy"),)), ("weight",), SETTINGS)

    outcome = asyncio.run(call_model(OfflineTransport(), request, parse_summary, SETTINGS))

    assert outcome.status == "ok"
    assert outcome.result is not None and outcome.result["summary"].startswith("Offline stand-in summary")

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.questions import SCHEMA_PATH, QuestionSchema, load_schema

NON_QUESTION_KINDS = {"interstitial", "health_benefit", "health_permission", "health_review", "voice"}


def _ids(mode: str) -> list[str]:
    return [screen.id for screen in load_schema().for_mode(mode)]  # type: ignore[arg-type]


def _raw() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())
    return raw


def test_schema_has_23_questions_and_7_health_linked() -> None:
    screens = load_schema().screens
    questions = [s for s in screens if s.kind not in NON_QUESTION_KINDS]
    facts = [s for s in questions if s.health and s.health.kind == "fact"]
    estimates = [s for s in questions if s.health and s.health.kind == "estimate"]

    assert len(questions) == 23
    assert len(facts) == 5
    assert len(estimates) == 2


def test_health_first_asks_permission_before_about_you_questions() -> None:
    ids = _ids("health_first")

    assert ids.index("health_benefit") < ids.index("health_permission_early")
    assert ids.index("health_permission_early") < ids.index("health_review")
    assert ids.index("health_review") < ids.index("gender_identity")
    assert "health_permission_late" not in ids


def test_today_asks_permission_after_about_you_like_the_current_flow() -> None:
    ids = _ids("today")

    assert ids.index("exercise_frequency") < ids.index("health_permission_late") < ids.index("steps")
    assert "health_review" not in ids
    assert "health_benefit" not in ids


def test_review_card_covers_every_health_linked_question() -> None:
    review = next(s for s in load_schema().screens if s.kind == "health_review")

    assert set(review.review_rows) == {
        "sex_at_birth",
        "date_of_birth",
        "height",
        "weight",
        "steps",
        "exercise_frequency",
        "activity_level",
    }


def test_voice_screens_cover_every_question_health_cannot_answer_except_gender() -> None:
    schema = load_schema()
    questions = {s.id for s in schema.for_mode("health_first") if s.kind not in NON_QUESTION_KINDS and s.health is None}

    assert schema.covered("health_first") == questions - {"gender_identity"}
    assert schema.covered("today") == frozenset()


def test_a_voice_screen_cannot_cover_a_health_question() -> None:
    raw = _raw()
    voice = next(s for s in raw["screens"] if s["id"] == "voice_goals")
    voice["covers"] = [*voice["covers"], "weight"]

    with pytest.raises(ValidationError, match="must be a question Health can't answer"):
        QuestionSchema.model_validate(raw)


def test_a_question_is_covered_once() -> None:
    raw = _raw()
    voice = next(s for s in raw["screens"] if s["id"] == "voice_food")
    voice["covers"] = [*voice["covers"], "main_goal"]

    with pytest.raises(ValidationError, match="covered by one voice screen only"):
        QuestionSchema.model_validate(raw)


def test_weight_can_always_be_skipped() -> None:
    weight = next(s for s in load_schema().screens if s.id == "weight")

    assert weight.optional
    assert weight.skip_label == "Add this later"


def test_duplicate_screen_ids_are_rejected() -> None:
    raw = _raw()
    raw["screens"].append(raw["screens"][0])

    with pytest.raises(ValidationError, match="screen ids must be unique"):
        QuestionSchema.model_validate(raw)


def test_permission_after_a_health_question_is_rejected_in_health_first() -> None:
    raw = _raw()
    screens = raw["screens"]
    early = next(s for s in screens if s["id"] == "health_permission_early")
    screens.remove(early)
    screens.append(early)

    with pytest.raises(ValidationError, match="permission must come before"):
        QuestionSchema.model_validate(raw)


def test_review_row_must_be_health_linked() -> None:
    raw = _raw()
    review = next(s for s in raw["screens"] if s["id"] == "health_review")
    review["review_rows"] = [*review["review_rows"], "meals_per_day"]

    with pytest.raises(ValidationError, match="must be a Health-linked screen"):
        QuestionSchema.model_validate(raw)


def test_unknown_rule_is_rejected() -> None:
    raw = _raw()
    steps = next(s for s in raw["screens"] if s["id"] == "steps")
    steps["health"]["rule"] = "made_up_rule"

    with pytest.raises(ValidationError):
        QuestionSchema.model_validate(raw)

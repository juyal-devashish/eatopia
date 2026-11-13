from app.answers import validate
from app.catalog import load_catalog
from app.questions import load_schema
from evals.voice_extract import OWN_WORDS, Case, CaseResult, judge, load_cases, score


def test_cases_cover_every_question_with_valid_answers() -> None:
    screens = {s.id: s for s in load_schema().screens}
    cases = load_cases()

    assert len(cases) >= 30
    assert len({c.id for c in cases}) == len(cases)
    for case in cases:
        assert set(case.expected) == set(screens[case.screen].covers), case.id
        for question, expected in case.expected.items():
            for value in expected["any_of"] if isinstance(expected, dict) and "any_of" in expected else [expected]:
                if value is not None and value != OWN_WORDS:
                    validate(screens[question], value)
    assert load_catalog()


def test_each_outcome_is_judged() -> None:
    assert judge("energy", "energy") == "correct"
    assert judge("energy", "weight") == "wrong"
    assert judge(None, "weight") == "invented"
    assert judge("energy", None) == "missed"
    assert judge(None, None) == "empty"
    assert judge(["dairy", "eggs"], ["eggs", "dairy"]) == "correct"
    assert judge(OWN_WORDS, "mushrooms") == "correct"
    assert judge({"any_of": [None, OWN_WORDS]}, None) == "empty"


def test_failed_attempts_leave_everything_empty_and_are_reported() -> None:
    case = Case(id="x", screen="voice_food", text="t", expected={"diet_pattern": "vegan", "allergies": None})
    summary = score([CaseResult(case=case, status="timeout", answers={"diet_pattern": "vegan"})])

    assert (summary["correct"], summary["missed"], summary["empty"]) == (0, 1, 1)
    assert summary["failed_attempts"] == 1

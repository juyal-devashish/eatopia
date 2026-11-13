from datetime import UTC, date, datetime, timedelta

import pytest

from app.config import RuleSettings
from app.health.members import load_member
from app.health.models import MemberId, resolve
from app.health.summary import DailySteps, HealthSummaryV1, Measurement, build_summary
from app.questions import load_schema
from app.rules import RuleResult, activity_level, exercise_bucket, steps_bucket, suggest

NOW = datetime(2026, 11, 13, 15, 30, tzinfo=UTC)
SETTINGS = RuleSettings()


def _results(member_id: MemberId) -> dict[str, RuleResult]:
    summary = build_summary(resolve(load_member(member_id), NOW), NOW)
    return suggest(load_schema(), summary, NOW, SETTINGS)


def _summary(**changes: object) -> HealthSummaryV1:
    base = HealthSummaryV1(
        generated_at=NOW,
        read_types_with_data=(),
        biological_sex=None,
        date_of_birth=None,
        latest_height=None,
        latest_weight=None,
        workouts_last_28d=0,
        workouts_recorded=0,
        daily_steps_30d=(),
    )
    return base.model_copy(update=changes)


def _weight_days_ago(days: int) -> Measurement:
    return Measurement(value=70.0, unit="kg", at=NOW - timedelta(days=days), source="test")


def _steps(count: int, days: int) -> tuple[DailySteps, ...]:
    return tuple(DailySteps(day=date(2026, 11, 12) - timedelta(days=i), count=count) for i in range(days))


def _rule(screen_id: str, summary: HealthSummaryV1) -> RuleResult:
    return suggest(load_schema(), summary, NOW, SETTINGS)[screen_id]


def test_member_a_gets_every_suggestion() -> None:
    results = _results("a")

    assert {k: (r.status, r.value) for k, r in results.items()} == {
        "sex_at_birth": ("suggested", "female"),
        "date_of_birth": ("suggested", "1990-03-14"),
        "height": ("suggested", {"cm": 168.3}),
        "weight": ("suggested", {"kg": 73.4}),
        "steps": ("suggested", "s9000_11999"),
        "exercise_frequency": ("suggested", "d5_6"),
        "activity_level": ("suggested", "very"),
    }


def test_member_b_asks_where_data_is_weak() -> None:
    results = _results("b")

    assert {k: r.status for k, r in results.items()} == {
        "sex_at_birth": "ask",
        "date_of_birth": "suggested",
        "height": "suggested",
        "weight": "ask",
        "steps": "suggested",
        "exercise_frequency": "ask",
        "activity_level": "suggested",
    }
    assert results["steps"].value == "s3000_5999"
    assert results["activity_level"].value == "light"
    assert "120 days old" in results["weight"].evidence
    assert "doesn't log" in results["exercise_frequency"].evidence


def test_member_c_asks_everything() -> None:
    assert {r.status for r in _results("c").values()} == {"ask"}


def test_estimates_and_facts_keep_their_kind() -> None:
    results = _results("a")

    assert results["exercise_frequency"].kind == "estimate"
    assert results["activity_level"].kind == "estimate"
    assert results["weight"].kind == "fact"


@pytest.mark.parametrize(
    ("days_ago", "status"),
    [(0, "suggested"), (30, "suggested"), (31, "needs_check"), (90, "needs_check"), (91, "ask")],
)
def test_weight_freshness_edges(days_ago: int, status: str) -> None:
    assert _rule("weight", _summary(latest_weight=_weight_days_ago(days_ago))).status == status


@pytest.mark.parametrize(("days", "status"), [(13, "ask"), (14, "suggested")])
def test_steps_need_14_days_of_data(days: int, status: str) -> None:
    summary = _summary(daily_steps_30d=_steps(8_000, days))

    assert _rule("steps", summary).status == status
    assert _rule("activity_level", summary).status == status


@pytest.mark.parametrize(
    ("median", "bucket"),
    [
        (2_999, "under_3000"),
        (3_000, "s3000_5999"),
        (5_999, "s3000_5999"),
        (6_000, "s6000_8999"),
        (11_999, "s9000_11999"),
        (12_000, "s12000_plus"),
    ],
)
def test_steps_bucket_edges(median: int, bucket: str) -> None:
    assert steps_bucket(median) == bucket


@pytest.mark.parametrize(
    ("median", "level"),
    [
        (4_999, "sedentary"),
        (5_000, "light"),
        (7_499, "light"),
        (7_500, "moderate"),
        (9_999, "moderate"),
        (10_000, "very"),
    ],
)
def test_activity_edges(median: int, level: str) -> None:
    assert activity_level(median, SETTINGS) == level


@pytest.mark.parametrize(
    ("per_week", "bucket"),
    [(0, "d0"), (0.25, "d0"), (0.5, "d1_2"), (2.25, "d1_2"), (2.5, "d3_4"), (4.5, "d5_6"), (6.5, "d7")],
)
def test_exercise_bucket_edges(per_week: float, bucket: str) -> None:
    assert exercise_bucket(per_week) == bucket


def test_no_recent_workouts_but_some_recorded_suggests_none() -> None:
    result = _rule("exercise_frequency", _summary(workouts_last_28d=0, workouts_recorded=12))

    assert (result.status, result.value) == ("suggested", "d0")


def test_implausible_values_are_asked() -> None:
    tall = Measurement(value=2.9, unit="m", at=NOW, source="test")
    young = date(2020, 1, 1)

    assert _rule("height", _summary(latest_height=tall)).status == "ask"
    assert _rule("date_of_birth", _summary(date_of_birth=young)).status == "ask"


def test_other_sex_is_asked() -> None:
    assert _rule("sex_at_birth", _summary(biological_sex="other")).status == "ask"


def test_every_rule_has_a_reason_when_it_asks() -> None:
    assert all(r.evidence for r in _results("c").values())

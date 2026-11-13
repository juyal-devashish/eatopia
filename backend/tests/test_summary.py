from datetime import UTC, date, datetime

import pytest

from app.health.members import load_member
from app.health.models import resolve
from app.health.summary import build_summary

NOW = datetime(2026, 11, 13, 15, 30, tzinfo=UTC)


def test_member_a_summary() -> None:
    summary = build_summary(resolve(load_member("a"), NOW), NOW)

    assert summary.biological_sex == "female"
    assert summary.date_of_birth == date(1990, 3, 14)
    assert summary.latest_weight is not None
    assert summary.latest_weight.value == 73.417
    assert summary.latest_weight.at == datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
    assert summary.latest_height is not None
    assert summary.latest_height.value == 1.6834
    assert len(summary.daily_steps_30d) == 30
    assert summary.workouts_last_28d == 22
    assert summary.workouts_recorded == 25
    assert "HKWorkoutTypeIdentifier" in summary.read_types_with_data


def test_member_b_summary_has_gaps_and_no_sex() -> None:
    summary = build_summary(resolve(load_member("b"), NOW), NOW)

    assert summary.biological_sex is None
    assert len(summary.daily_steps_30d) == 18
    assert summary.workouts_recorded == 0
    assert "HKCharacteristicTypeIdentifierBiologicalSex" not in summary.read_types_with_data


def test_member_c_summary_is_empty() -> None:
    summary = build_summary(resolve(load_member("c"), NOW), NOW)

    assert summary.read_types_with_data == ()
    assert summary.latest_weight is None
    assert summary.daily_steps_30d == ()


def test_samples_after_now_are_ignored() -> None:
    earlier = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    summary = build_summary(resolve(load_member("a"), NOW), earlier)

    assert summary.latest_weight is not None
    assert summary.latest_weight.value == 73.9


@pytest.mark.parametrize("hour", [0, 9, 15, 18, 23])
def test_workout_count_does_not_depend_on_the_time_of_day(hour: int) -> None:
    now = NOW.replace(hour=hour, minute=30)

    assert build_summary(resolve(load_member("a"), now), now).workouts_last_28d == 22

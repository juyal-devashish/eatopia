from datetime import UTC, datetime, timedelta

import pytest

from app.health.members import MEMBER_IDS, load_member
from app.health.models import MemberId, resolve
from app.health.synthetic import MEMBERS_DIR, build_members, render

NOW = datetime(2026, 11, 13, 15, 30, tzinfo=UTC)


def test_committed_fixtures_match_the_seeded_generator() -> None:
    for member_id, fixture in build_members().items():
        assert (MEMBERS_DIR / f"{member_id}.json").read_text() == render(fixture)


@pytest.mark.parametrize("member_id", MEMBER_IDS)
def test_every_member_is_marked_synthetic(member_id: MemberId) -> None:
    assert load_member(member_id).synthetic is True


def test_dates_resolve_relative_to_the_clock() -> None:
    data = resolve(load_member("a"), NOW)
    weights = [s for s in data.quantity_samples if s.type == "HKQuantityTypeIdentifierBodyMass"]
    latest = max(weights, key=lambda s: s.end)

    assert latest.end == datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
    assert latest.value == pytest.approx(73.417)


def test_step_samples_cover_whole_days() -> None:
    data = resolve(load_member("a"), NOW)
    steps = [s for s in data.quantity_samples if s.type == "HKQuantityTypeIdentifierStepCount"]

    assert len(steps) == 30
    assert all(s.end - s.start == timedelta(days=1) for s in steps)
    assert max(s.end for s in steps) == datetime(2026, 11, 13, tzinfo=UTC)


def test_member_b_has_gaps_old_weight_and_no_workouts() -> None:
    fixture = load_member("b")
    steps = [s for s in fixture.quantity_samples if s.type == "HKQuantityTypeIdentifierStepCount"]
    weight = next(s for s in fixture.quantity_samples if s.type == "HKQuantityTypeIdentifierBodyMass")

    assert len(steps) == 18
    assert weight.days_ago > 90
    assert fixture.workouts == ()
    assert fixture.biological_sex == "notSet"


def test_member_c_has_no_data() -> None:
    data = resolve(load_member("c"), NOW)

    assert data.quantity_samples == ()
    assert data.workouts == ()
    assert data.date_of_birth is None


def test_canary_values_are_real_values_in_the_fixture() -> None:
    for member_id in MEMBER_IDS:
        fixture = load_member(member_id)
        values = {repr(s.value) for s in fixture.quantity_samples}
        for canary in fixture.canary_values:
            assert canary in values


def test_resolve_needs_a_timezone_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        resolve(load_member("a"), datetime(2026, 11, 13))

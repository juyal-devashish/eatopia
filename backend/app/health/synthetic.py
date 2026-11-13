"""Builds the three synthetic members. Seeded, so the output is identical on every run.

Regenerate the committed fixtures with: `uv run python -m app.health.synthetic`
"""

import random
from datetime import date
from pathlib import Path

from app.health.models import MemberFixture, MemberId, QuantitySampleSpec, WorkoutSpec

MEMBERS_DIR = Path(__file__).parent.parent / "data" / "members"
WATCH = "Watch (synthetic)"
PHONE = "iPhone (synthetic)"
SCALE = "Smart scale (synthetic)"


def _steps(
    rng: random.Random, days: list[int], mean: int, spread: int, source: str
) -> list[QuantitySampleSpec]:
    return [
        QuantitySampleSpec(
            type="HKQuantityTypeIdentifierStepCount",
            value=max(0, round(rng.gauss(mean, spread))),
            unit="count",
            days_ago=day,
            source=source,
        )
        for day in days
    ]


def _member_a() -> MemberFixture:
    rng = random.Random(1001)
    workout_days = sorted(rng.sample(range(1, 29), 22)) + [33, 36, 40]
    return MemberFixture(
        id="a",
        label="Wears a watch",
        description="Everything recorded and recent.",
        synthetic=True,
        canary_values=("73.417", "1.6834"),
        biological_sex="female",
        date_of_birth=date(1990, 3, 14),
        quantity_samples=(
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierHeight",
                value=1.6834,
                unit="m",
                days_ago=410,
                source=PHONE,
            ),
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierBodyMass",
                value=73.417,
                unit="kg",
                days_ago=3,
                source=SCALE,
            ),
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierBodyMass",
                value=73.9,
                unit="kg",
                days_ago=17,
                source=SCALE,
            ),
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierBodyMass",
                value=74.6,
                unit="kg",
                days_ago=45,
                source=SCALE,
            ),
            *_steps(rng, list(range(1, 31)), mean=10_400, spread=1_900, source=WATCH),
        ),
        workouts=tuple(
            WorkoutSpec(
                activity_type=rng.choice(
                    [
                        "HKWorkoutActivityTypeRunning",
                        "HKWorkoutActivityTypeTraditionalStrengthTraining",
                        "HKWorkoutActivityTypeCycling",
                    ]
                ),
                days_ago=day,
                duration_minutes=rng.randint(25, 60),
                source=WATCH,
            )
            for day in workout_days
        ),
    )


def _member_b() -> MemberFixture:
    rng = random.Random(2002)
    step_days = sorted(rng.sample(range(1, 31), 18))
    return MemberFixture(
        id="b",
        label="Phone only",
        description="Steps with gaps, weight four months old, no workouts, sex not set.",
        synthetic=True,
        canary_values=("81.263", "1.7752"),
        biological_sex="notSet",
        date_of_birth=date(1984, 11, 2),
        quantity_samples=(
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierHeight",
                value=1.7752,
                unit="m",
                days_ago=800,
                source=PHONE,
            ),
            QuantitySampleSpec(
                type="HKQuantityTypeIdentifierBodyMass",
                value=81.263,
                unit="kg",
                days_ago=120,
                source=PHONE,
            ),
            *_steps(rng, step_days, mean=5_300, spread=1_100, source=PHONE),
        ),
        workouts=(),
    )


def _member_c() -> MemberFixture:
    return MemberFixture(
        id="c",
        label="No data",
        description="Nothing in Apple Health, or access denied. HealthKit can't tell the two apart.",
        synthetic=True,
        canary_values=(),
        biological_sex="notSet",
        date_of_birth=None,
        quantity_samples=(),
        workouts=(),
    )


def build_members() -> dict[MemberId, MemberFixture]:
    return {"a": _member_a(), "b": _member_b(), "c": _member_c()}


def render(fixture: MemberFixture) -> str:
    return fixture.model_dump_json(indent=2) + "\n"


def main() -> None:
    for member_id, fixture in build_members().items():
        (MEMBERS_DIR / f"{member_id}.json").write_text(render(fixture))


if __name__ == "__main__":
    main()

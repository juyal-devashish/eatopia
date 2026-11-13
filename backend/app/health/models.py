"""HealthKit-shaped data for the synthetic members.

Fixtures store dates as "days ago" so the demo never goes stale; `resolve` turns them into timestamps
against an injected clock. Every value here is device data: it never goes to the language model.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

BiologicalSex = Literal["female", "male", "other", "notSet"]
QuantityType = Literal[
    "HKQuantityTypeIdentifierHeight",
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierStepCount",
]
Unit = Literal["m", "kg", "count"]
UNIT_FOR_TYPE: dict[QuantityType, Unit] = {
    "HKQuantityTypeIdentifierHeight": "m",
    "HKQuantityTypeIdentifierBodyMass": "kg",
    "HKQuantityTypeIdentifierStepCount": "count",
}
MemberId = Literal["a", "b", "c"]

# Point samples (height, weight) are taken at 08:00; workouts start at 18:00; step totals cover a whole day.
POINT_SAMPLE_TIME = time(8, 0)
WORKOUT_START_TIME = time(18, 0)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QuantitySampleSpec(_Strict):
    type: QuantityType
    value: float = Field(ge=0)
    unit: Unit
    days_ago: int = Field(ge=0)
    source: str

    @model_validator(mode="after")
    def _unit_matches_type(self) -> Self:
        if UNIT_FOR_TYPE[self.type] != self.unit:
            raise ValueError(f"{self.type} must use unit {UNIT_FOR_TYPE[self.type]}")
        return self


class WorkoutSpec(_Strict):
    activity_type: str
    days_ago: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    source: str


class MemberFixture(_Strict):
    id: MemberId
    label: str
    description: str
    synthetic: Literal[True]
    canary_values: tuple[str, ...]
    biological_sex: BiologicalSex
    date_of_birth: date | None
    quantity_samples: tuple[QuantitySampleSpec, ...]
    workouts: tuple[WorkoutSpec, ...]


class QuantitySample(_Strict):
    type: QuantityType
    value: float
    unit: Unit
    start: datetime
    end: datetime
    source: str


class Workout(_Strict):
    activity_type: str
    start: datetime
    end: datetime
    source: str


class MemberHealthData(_Strict):
    member_id: MemberId
    biological_sex: BiologicalSex
    date_of_birth: date | None
    quantity_samples: tuple[QuantitySample, ...]
    workouts: tuple[Workout, ...]


def _day_start(now: datetime, days_ago: int) -> datetime:
    today = datetime.combine(now.astimezone(UTC).date(), time(0, 0), tzinfo=UTC)
    return today - timedelta(days=days_ago)


def resolve(fixture: MemberFixture, now: datetime) -> MemberHealthData:
    """Turn "days ago" offsets into timestamps relative to `now` (timezone-aware)."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    samples = []
    for spec in fixture.quantity_samples:
        day = _day_start(now, spec.days_ago)
        if spec.type == "HKQuantityTypeIdentifierStepCount":
            start, end = day, day + timedelta(days=1)
        else:
            start = end = datetime.combine(day.date(), POINT_SAMPLE_TIME, tzinfo=UTC)
        samples.append(
            QuantitySample(
                type=spec.type,
                value=spec.value,
                unit=spec.unit,
                start=start,
                end=end,
                source=spec.source,
            )
        )
    workouts = []
    for workout in fixture.workouts:
        day = _day_start(now, workout.days_ago)
        start = datetime.combine(day.date(), WORKOUT_START_TIME, tzinfo=UTC)
        workouts.append(
            Workout(
                activity_type=workout.activity_type,
                start=start,
                end=start + timedelta(minutes=workout.duration_minutes),
                source=workout.source,
            )
        )
    return MemberHealthData(
        member_id=fixture.id,
        biological_sex=fixture.biological_sex,
        date_of_birth=fixture.date_of_birth,
        quantity_samples=tuple(samples),
        workouts=tuple(workouts),
    )

"""HealthSummaryV1: the compact summary an iPhone would send after reading HealthKit.

This is the integration contract. A real iOS app would build it on the device and send it with
`POST /sessions/{id}/health-summary`; the demo builds it on the server from synthetic samples instead.
Everything in it is device data and never goes to the language model.
"""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.health.models import BiologicalSex, MemberHealthData, QuantitySample, Unit

STEP_WINDOW_DAYS = 30
WORKOUT_WINDOW_DAYS = 28


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Measurement(_Strict):
    value: float
    unit: Unit
    at: datetime
    source: str


class DailySteps(_Strict):
    day: date
    count: int


class HealthSummaryV1(_Strict):
    schema_version: Literal[1] = 1
    generated_at: datetime
    read_types_with_data: tuple[str, ...]
    biological_sex: BiologicalSex | None
    date_of_birth: date | None
    latest_height: Measurement | None
    latest_weight: Measurement | None
    workouts_last_28d: int
    workouts_recorded: int
    daily_steps_30d: tuple[DailySteps, ...]


def _latest(samples: list[QuantitySample]) -> Measurement | None:
    if not samples:
        return None
    sample = max(samples, key=lambda s: s.end)
    return Measurement(value=sample.value, unit=sample.unit, at=sample.end, source=sample.source)


def build_summary(data: MemberHealthData, now: datetime) -> HealthSummaryV1:
    """What the iPhone side would compute from HealthKit. Only data up to `now` counts."""
    by_type: dict[str, list[QuantitySample]] = defaultdict(list)
    for sample in data.quantity_samples:
        if sample.end <= now:
            by_type[sample.type].append(sample)

    today = datetime.combine(now.astimezone(UTC).date(), time(0, 0), tzinfo=UTC)
    step_window_start = today - timedelta(days=STEP_WINDOW_DAYS)
    steps_per_day: dict[date, float] = defaultdict(float)
    for sample in by_type["HKQuantityTypeIdentifierStepCount"]:
        if sample.start >= step_window_start:
            steps_per_day[sample.start.date()] += sample.value

    workouts = [w for w in data.workouts if w.start <= now]
    workout_window_start = now - timedelta(days=WORKOUT_WINDOW_DAYS)

    read_types = sorted(type_id for type_id, samples in by_type.items() if samples)
    if data.biological_sex != "notSet":
        read_types.append("HKCharacteristicTypeIdentifierBiologicalSex")
    if data.date_of_birth is not None:
        read_types.append("HKCharacteristicTypeIdentifierDateOfBirth")
    if workouts:
        read_types.append("HKWorkoutTypeIdentifier")

    return HealthSummaryV1(
        generated_at=now,
        read_types_with_data=tuple(read_types),
        biological_sex=None if data.biological_sex == "notSet" else data.biological_sex,
        date_of_birth=data.date_of_birth,
        latest_height=_latest(by_type["HKQuantityTypeIdentifierHeight"]),
        latest_weight=_latest(by_type["HKQuantityTypeIdentifierBodyMass"]),
        workouts_last_28d=sum(1 for w in workouts if w.start >= workout_window_start),
        workouts_recorded=len(workouts),
        daily_steps_30d=tuple(
            DailySteps(day=day, count=round(count)) for day, count in sorted(steps_per_day.items())
        ),
    )

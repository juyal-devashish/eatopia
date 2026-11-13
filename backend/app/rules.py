"""Mapping rules: Health summary -> suggested answers. Plain code, no model calls.

Each rule either suggests an answer (with the evidence behind it) or says why the question should be
asked as today. Weak data is never guessed. Thresholds come from `RuleSettings`.
"""

import math
import statistics
from collections.abc import Callable
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from app.config import RuleSettings
from app.health.summary import HealthSummaryV1
from app.questions import HealthLink, QuestionSchema, RuleId

RULE_VERSION = "v1"
Status = Literal["suggested", "needs_check", "ask"]


class RuleResult(BaseModel):
    """One rule's outcome. `value` and `evidence` are device data: shown to the member, never the model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    screen_id: str
    rule: RuleId
    version: str = RULE_VERSION
    kind: Literal["fact", "estimate"]
    status: Status
    value: JsonValue = None
    evidence: str
    source: str | None = None
    observed_at: datetime | None = None


class _Outcome(BaseModel):
    status: Status
    value: JsonValue = None
    evidence: str
    source: str | None = None
    observed_at: datetime | None = None


def _ask(reason: str) -> _Outcome:
    return _Outcome(status="ask", evidence=reason)


def _age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def steps_bucket(median: float) -> str:
    if median < 3_000:
        return "under_3000"
    if median < 6_000:
        return "s3000_5999"
    if median < 9_000:
        return "s6000_8999"
    if median < 12_000:
        return "s9000_11999"
    return "s12000_plus"


def exercise_bucket(per_week: float) -> str:
    days = _round_half_up(per_week)
    if days <= 0:
        return "d0"
    if days <= 2:
        return "d1_2"
    if days <= 4:
        return "d3_4"
    if days <= 6:
        return "d5_6"
    return "d7"


def activity_level(median: float, settings: RuleSettings) -> str:
    if median < settings.activity_light_from:
        return "sedentary"
    if median < settings.activity_moderate_from:
        return "light"
    if median < settings.activity_very_from:
        return "moderate"
    return "very"


def _step_median(summary: HealthSummaryV1, settings: RuleSettings) -> tuple[float, int] | None:
    days = len(summary.daily_steps_30d)
    if days < settings.steps_min_days:
        return None
    return statistics.median(d.count for d in summary.daily_steps_30d), days


def _sex_at_birth(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    if summary.biological_sex in ("female", "male"):
        return _Outcome(status="suggested", value=summary.biological_sex, evidence="Sex set in Apple Health")
    return _ask("Sex isn't set in Apple Health")


def _date_of_birth(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    birth = summary.date_of_birth
    if birth is None:
        return _ask("Date of birth isn't set in Apple Health")
    age = _age_on(birth, now.date())
    if not settings.min_age <= age <= settings.max_age:
        return _ask("Date of birth in Apple Health looks wrong")
    return _Outcome(status="suggested", value=birth.isoformat(), evidence="Date of birth in Apple Health")


def _height_latest(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    height = summary.latest_height
    if height is None:
        return _ask("No height in Apple Health")
    cm = round(height.value * 100, 1)
    if not settings.min_height_cm <= cm <= settings.max_height_cm:
        return _ask("Height in Apple Health looks wrong")
    return _Outcome(
        status="suggested",
        value={"cm": cm},
        evidence="Latest height in Apple Health",
        source=height.source,
        observed_at=height.at,
    )


def _weight_recent(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    weight = summary.latest_weight
    if weight is None:
        return _ask("No weight in Apple Health")
    age_days = (now - weight.at).days
    if age_days > settings.weight_max_age_days:
        return _ask(f"Latest weight in Apple Health is {age_days} days old")
    kg = round(weight.value, 1)
    if not settings.min_weight_kg <= kg <= settings.max_weight_kg:
        return _ask("Weight in Apple Health looks wrong")
    status: Status = "suggested" if age_days <= settings.weight_fresh_days else "needs_check"
    return _Outcome(
        status=status,
        value={"kg": kg},
        evidence=f"Latest weight in Apple Health, {age_days} days ago",
        source=weight.source,
        observed_at=weight.at,
    )


def _steps_median_30d(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    result = _step_median(summary, settings)
    if result is None:
        return _ask(f"Steps recorded on fewer than {settings.steps_min_days} of the last 30 days")
    median, days = result
    return _Outcome(
        status="suggested",
        value=steps_bucket(median),
        evidence=f"Median of {round(median):,} steps a day over {days} days with data",
    )


def _exercise_per_week(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    if summary.workouts_recorded == 0:
        return _ask("No workouts ever recorded, so we can't tell 'doesn't exercise' from 'doesn't log'")
    per_week = summary.workouts_last_28d / 4
    return _Outcome(
        status="suggested",
        value=exercise_bucket(per_week),
        evidence=f"{summary.workouts_last_28d} workouts in the last 4 weeks",
    )


def _activity_from_steps(summary: HealthSummaryV1, now: datetime, settings: RuleSettings) -> _Outcome:
    result = _step_median(summary, settings)
    if result is None:
        return _ask("Not enough step data to estimate")
    median, _ = result
    return _Outcome(
        status="suggested",
        value=activity_level(median, settings),
        evidence=f"Estimated from a median of {round(median):,} steps a day",
    )


RuleFn = Callable[[HealthSummaryV1, datetime, RuleSettings], _Outcome]
RULES: dict[RuleId, RuleFn] = {
    "sex_at_birth": _sex_at_birth,
    "date_of_birth": _date_of_birth,
    "height_latest": _height_latest,
    "weight_recent": _weight_recent,
    "steps_median_30d": _steps_median_30d,
    "exercise_per_week": _exercise_per_week,
    "activity_from_steps": _activity_from_steps,
}


def run_rule(
    screen_id: str, link: HealthLink, summary: HealthSummaryV1, now: datetime, settings: RuleSettings
) -> RuleResult:
    outcome = RULES[link.rule](summary, now, settings)
    return RuleResult(screen_id=screen_id, rule=link.rule, kind=link.kind, **outcome.model_dump())


def suggest(
    schema: QuestionSchema, summary: HealthSummaryV1, now: datetime, settings: RuleSettings
) -> dict[str, RuleResult]:
    """Run every Health-linked screen's rule. Keyed by screen id."""
    return {
        screen.id: run_rule(screen.id, screen.health, summary, now, settings)
        for screen in schema.screens
        if screen.health is not None
    }

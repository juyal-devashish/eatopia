"""The onboarding question schema: sections, screens and which Health rule can answer each.

The schema is data (`app/data/questions.json`); this module validates it once at load time so a bad edit
fails fast in tests instead of in the browser.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["today", "health_first"]
MODES: tuple[Mode, ...] = ("today", "health_first")

ScreenKind = Literal[
    "single_choice",
    "multi_choice",
    "date",
    "height",
    "weight",
    "text",
    "interstitial",
    "condition_picker",
    "health_benefit",
    "health_permission",
    "health_review",
]
CHOICE_KINDS: frozenset[str] = frozenset({"single_choice", "multi_choice"})

# Rules are implemented in M2. Listing them here keeps the schema from naming a rule that doesn't exist.
RuleId = Literal[
    "sex_at_birth",
    "date_of_birth",
    "height_latest",
    "weight_recent",
    "steps_median_30d",
    "exercise_per_week",
    "activity_from_steps",
]

SCHEMA_PATH = Path(__file__).parent / "data" / "questions.json"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Section(_Strict):
    id: str
    title: str
    assumed: bool = False


class Option(_Strict):
    id: str
    label: str
    free_text: bool = False
    exclusive: bool = False


class HealthLink(_Strict):
    kind: Literal["fact", "estimate"]
    rule: RuleId


class Screen(_Strict):
    id: str
    section: str
    kind: ScreenKind
    title: str
    subtitle: str | None = None
    options: tuple[Option, ...] = ()
    optional: bool = False
    skip_label: str | None = None
    units: tuple[str, ...] = ()
    health: HealthLink | None = None
    modes: tuple[Mode, ...] = MODES
    catalog: str | None = None
    review_rows: tuple[str, ...] = ()
    read_types: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        if self.kind in CHOICE_KINDS and not self.options:
            raise ValueError(f"{self.id}: choice screens need options")
        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError(f"{self.id}: option ids must be unique")
        if self.optional != (self.skip_label is not None):
            raise ValueError(f"{self.id}: optional screens need a skip label, and only they have one")
        if (self.kind == "health_review") != bool(self.review_rows):
            raise ValueError(f"{self.id}: only the review card has review rows, and it needs some")
        if (self.kind == "health_permission") != bool(self.read_types):
            raise ValueError(f"{self.id}: only permission screens list read types, and they need some")
        return self


class QuestionSchema(_Strict):
    version: int
    note: str
    sections: tuple[Section, ...]
    screens: tuple[Screen, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        section_ids = {section.id for section in self.sections}
        screen_ids = [screen.id for screen in self.screens]
        if len(screen_ids) != len(set(screen_ids)):
            raise ValueError("screen ids must be unique")
        by_id = {screen.id: screen for screen in self.screens}

        for screen in self.screens:
            if screen.section not in section_ids:
                raise ValueError(f"{screen.id}: unknown section {screen.section}")
            for row in screen.review_rows:
                target = by_id.get(row)
                if target is None or target.health is None or target.health.kind != "fact":
                    raise ValueError(f"{screen.id}: review row {row} must be a Health fact screen")

        fact_ids = {s.id for s in self.screens if s.health is not None and s.health.kind == "fact"}
        for mode in MODES:
            screens = self.for_mode(mode)
            permissions = [i for i, s in enumerate(screens) if s.kind == "health_permission"]
            if len(permissions) != 1:
                raise ValueError(f"{mode}: needs exactly one Health permission screen")
            reviews = [s for s in screens if s.kind == "health_review"]
            if mode == "health_first":
                first_linked = min(i for i, s in enumerate(screens) if s.health is not None)
                if permissions[0] > first_linked:
                    raise ValueError("health_first: permission must come before any Health-linked question")
                if len(reviews) != 1 or set(reviews[0].review_rows) != fact_ids:
                    raise ValueError("health_first: one review card must cover every Health fact")
            elif reviews:
                raise ValueError(f"{mode}: has no review card")
        return self

    def for_mode(self, mode: Mode) -> tuple[Screen, ...]:
        return tuple(screen for screen in self.screens if mode in screen.modes)


@lru_cache
def load_schema(path: Path = SCHEMA_PATH) -> QuestionSchema:
    return QuestionSchema.model_validate_json(path.read_text())

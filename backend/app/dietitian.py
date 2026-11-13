"""The dietitian's view of an intake: answers as readable text, and the summary's Health placeholders.

The model writes the summary from `member_answers` only, which leaves out every Health-linked question. Health
values reach the summary afterwards, here, when `fill_placeholders` swaps `{{weight}}` and friends for the
member's answers.
"""

import re
from datetime import date
from typing import Any

from app.catalog import ConditionCatalog
from app.claude_client import MemberAnswers, MemberText
from app.questions import QuestionSchema, Screen

NOT_PROVIDED = "not provided"
NON_QUESTIONS = {"interstitial", "health_benefit", "health_permission", "health_review"}
FREE_TEXT_CHARS = 1_000
_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def placeholders(schema: QuestionSchema) -> tuple[str, ...]:
    """The Health-linked questions, which the summary may only mention by placeholder."""
    return tuple(s.id for s in schema.screens if s.health is not None)


def _member_text(text: str) -> str:
    return MemberText.from_member(text, FREE_TEXT_CHARS).text


def _choice(screen: Screen, item: Any, scrub: bool) -> str:
    if isinstance(item, dict) and "text" in item:
        return _member_text(str(item["text"])) if scrub else str(item["text"])
    return next((o.label for o in screen.options if o.id == item), str(item))


def format_answer(screen: Screen, value: Any, catalog: ConditionCatalog, scrub: bool = False) -> str:
    """An answer as a dietitian would read it. With `scrub`, free text has identifiers removed (for the model)."""
    if value is None:
        return screen.skip_label or "Skipped"
    match screen.kind:
        case "single_choice":
            return _choice(screen, value, scrub)
        case "multi_choice":
            return ", ".join(_choice(screen, item, scrub) for item in value)
        case "date":
            return date.fromisoformat(value).strftime("%-d %B %Y")
        case "height":
            cm = float(value["cm"])
            inches = round(cm / 2.54)
            return f"{inches // 12} ft {inches % 12} in ({cm:g} cm)"
        case "weight":
            kg = float(value["kg"])
            return f"{round(kg / 0.45359237)} lb ({kg:g} kg)"
        case "text":
            return _member_text(value) if scrub else str(value)
        case "condition_picker":
            if isinstance(value, dict) and "condition_id" in value:
                return next((c.label for c in catalog.conditions if c.id == value["condition_id"]), "Unknown")
            return _choice(screen, value, scrub)
        case _:
            return str(value)


def member_answers(schema: QuestionSchema, answers: dict[str, Any], catalog: ConditionCatalog) -> MemberAnswers:
    """What the summary model may read: answered questions that are not Health-linked, as text."""
    items = []
    for screen in schema.screens:
        if screen.kind in NON_QUESTIONS or screen.health is not None or screen.id not in answers:
            continue
        items.append((screen.title, format_answer(screen, answers[screen.id], catalog, scrub=True)))
    return MemberAnswers(items=tuple(items))


# How each Health-linked answer reads inside a sentence of the summary.
_PHRASES: dict[str, dict[str, str]] = {
    "exercise_frequency": {
        "d0": "doesn't exercise regularly",
        "d1_2": "exercises 1 to 2 days a week",
        "d3_4": "exercises 3 to 4 days a week",
        "d5_6": "exercises 5 to 6 days a week",
        "d7": "exercises every day",
        "varies": "exercises on a schedule that varies a lot",
    },
    "activity_level": {
        "sedentary": "is mostly sitting during the day",
        "light": "is lightly active day to day",
        "moderate": "is moderately active day to day",
        "very": "is very active day to day",
        "varies": "has activity that varies a lot from day to day",
    },
}


def _phrase(screen: Screen, value: Any, catalog: ConditionCatalog) -> str:
    """An answer as a short phrase that reads naturally mid-sentence."""
    if screen.id in _PHRASES and isinstance(value, str):
        return _PHRASES[screen.id].get(value, format_answer(screen, value, catalog).lower())
    match screen.id:
        case "sex_at_birth":
            return f"assigned {format_answer(screen, value, catalog).lower()} at birth"
        case "date_of_birth":
            return f"born {format_answer(screen, value, catalog)}"
        case "height":
            return f"{format_answer(screen, value, catalog)} tall"
        case "steps":
            return (
                "an unknown number of steps a day"
                if value == "not_sure"
                else f"{format_answer(screen, value, catalog)} steps a day"
            )
        case _:
            return format_answer(screen, value, catalog)


def fill_placeholders(
    summary: str, schema: QuestionSchema, answers: dict[str, Any], catalog: ConditionCatalog
) -> tuple[str, list[str]]:
    """Put the member's Health-linked answers in place of `{{name}}`. Returns the text and the names filled."""
    screens = {s.id: s for s in schema.screens}
    allowed = set(placeholders(schema))
    used: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in allowed:
            return NOT_PROVIDED
        used.append(name)
        if answers.get(name) is None:
            return NOT_PROVIDED
        return _phrase(screens[name], answers[name], catalog)

    return _PLACEHOLDER.sub(replace, summary), used


def template_summary(status: str) -> str:
    reason = "the daily limit was reached" if status == "capped" else "the summary couldn't be written"
    return f"No written summary for this intake ({reason}). Every answer is listed below with where it came from."

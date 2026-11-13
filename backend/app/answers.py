"""Checks a submitted answer against its screen in the question schema."""

from datetime import date
from typing import Any

from app.catalog import load_catalog
from app.questions import Screen

MAX_TEXT = 1000
HEIGHT_CM = (50.0, 272.0)
WEIGHT_KG = (20.0, 400.0)


class InvalidAnswer(ValueError):
    pass


def _choice(screen: Screen, item: Any) -> str:
    """A choice is an option id, or {"option": id, "text": ...} for a "Something else" option."""
    options = {option.id: option for option in screen.options}
    if isinstance(item, str) and item in options:
        return item
    if isinstance(item, dict) and set(item) == {"option", "text"}:
        option = options.get(item["option"])
        text = item["text"]
        if option is not None and option.free_text and isinstance(text, str) and 0 < len(text) <= MAX_TEXT:
            return option.id
    raise InvalidAnswer(f"{screen.id}: not a valid choice")


def _number(value: Any, key: str, bounds: tuple[float, float], screen_id: str) -> None:
    if not (isinstance(value, dict) and set(value) == {key}):
        raise InvalidAnswer(f"{screen_id}: expected {{'{key}': number}}")
    number = value[key]
    if isinstance(number, bool) or not isinstance(number, int | float) or not bounds[0] <= number <= bounds[1]:
        raise InvalidAnswer(f"{screen_id}: {key} out of range")


def validate(screen: Screen, value: Any) -> None:
    """Raise InvalidAnswer unless `value` fits the screen. `None` means skipped (optional screens only)."""
    if value is None:
        if screen.optional:
            return
        raise InvalidAnswer(f"{screen.id}: an answer is required")

    match screen.kind:
        case "single_choice":
            _choice(screen, value)
        case "multi_choice":
            if not isinstance(value, list) or not value:
                raise InvalidAnswer(f"{screen.id}: pick at least one option")
            picked = [_choice(screen, item) for item in value]
            if len(picked) != len(set(picked)):
                raise InvalidAnswer(f"{screen.id}: an option is picked twice")
            exclusive = {o.id for o in screen.options if o.exclusive}
            if exclusive & set(picked) and len(picked) > 1:
                raise InvalidAnswer(f"{screen.id}: that option can't be combined with others")
        case "date":
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError) as error:
                raise InvalidAnswer(f"{screen.id}: expected an ISO date") from error
        case "height":
            _number(value, "cm", HEIGHT_CM, screen.id)
        case "weight":
            _number(value, "kg", WEIGHT_KG, screen.id)
        case "text":
            if not isinstance(value, str) or not 0 < len(value) <= MAX_TEXT:
                raise InvalidAnswer(f"{screen.id}: text must be 1 to {MAX_TEXT} characters")
        case "condition_picker":
            if isinstance(value, str) and value in {o.id for o in screen.options}:
                return
            if not (isinstance(value, dict) and set(value) == {"condition_id"}):
                raise InvalidAnswer(f"{screen.id}: expected a condition id")
            if value["condition_id"] not in load_catalog().ids():
                raise InvalidAnswer(f"{screen.id}: unknown condition")
        case "interstitial" | "health_benefit":
            if value != {"seen": True}:
                raise InvalidAnswer(f"{screen.id}: expected {{'seen': true}}")
        case "health_permission":
            if not (isinstance(value, dict) and set(value) == {"granted"} and isinstance(value["granted"], bool)):
                raise InvalidAnswer(f"{screen.id}: expected {{'granted': true or false}}")
        case "health_review" | "voice":
            raise InvalidAnswer(f"{screen.id}: submit this screen with its rows")

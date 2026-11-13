"""What the same questions cost asked one per screen, for the finish screen's comparison.

Worked out from the question schema, not from a run: every screen Today's order shows, and the fewest taps each
could take. It is a lower bound, so the comparison can only understate the saving.
"""

from pydantic import BaseModel

from app.questions import QuestionSchema, Screen, ScreenKind

# Fewest taps to get past one screen of each kind. Typing is not counted as taps.
MIN_TAPS: dict[ScreenKind, int] = {
    "single_choice": 2,  # pick, Continue
    "multi_choice": 2,  # pick one, Continue
    "date": 4,  # month, day, year, Continue
    "height": 3,  # feet field, inches field, Continue
    "weight": 2,  # field, Continue
    "text": 2,  # field, Continue
    "condition_picker": 2,  # pick, Continue
    "interstitial": 1,  # Continue
    "health_benefit": 1,  # Continue
    "health_permission": 1,  # Allow
    "health_review": 1,  # Confirm
}


class Baseline(BaseModel):
    screens: int
    min_taps: int


def min_taps(screen: Screen) -> int:
    # An optional screen can be skipped with one tap.
    return 1 if screen.optional else MIN_TAPS[screen.kind]


def one_per_screen(schema: QuestionSchema) -> Baseline:
    screens = schema.for_mode("today")
    return Baseline(screens=len(screens), min_taps=sum(min_taps(s) for s in screens))

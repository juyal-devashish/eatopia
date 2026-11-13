from app.baseline import MIN_TAPS, min_taps, one_per_screen
from app.questions import load_schema


def test_every_screen_kind_has_a_tap_count() -> None:
    assert {s.kind for s in load_schema().screens} <= set(MIN_TAPS)


def test_optional_screens_count_one_tap_to_skip() -> None:
    weight = next(s for s in load_schema().screens if s.id == "weight")
    assert min_taps(weight) == 1


def test_baseline_counts_todays_order() -> None:
    schema = load_schema()
    baseline = one_per_screen(schema)

    assert baseline.screens == len(schema.for_mode("today")) == 25
    assert baseline.min_taps == sum(min_taps(s) for s in schema.for_mode("today"))
    assert baseline.min_taps > baseline.screens

from app.catalog import load_catalog
from evals.condition_match import Case, CaseResult, load_cases, score


def _result(expected: tuple[str, ...], matches: tuple[str, ...], status: str = "ok") -> CaseResult:
    return CaseResult(case=Case(id="x", text="t", expected=expected), status=status, matches=matches)


def test_cases_are_valid() -> None:
    cases = load_cases()
    known = load_catalog().ids()

    assert len(cases) >= 50
    assert len({c.id for c in cases}) == len(cases)
    assert all(set(c.expected) <= known for c in cases)
    assert sum(1 for c in cases if not c.expected) >= 5


def test_scoring_counts_hits_misses_and_no_match() -> None:
    summary = score(
        [
            _result(("gout",), ("gout", "anemia")),  # top-1 and top-3
            _result(("gout",), ("anemia", "gout")),  # top-3 only, wrong first
            _result(("gout",), ()),  # miss, nothing suggested
            _result((), ()),  # correct no match
            _result((), ("gout",)),  # suggested when nothing fits
        ]
    )

    assert (summary["top1_correct"], summary["top3_hit"], summary["wrong_first_suggestion"]) == (1, 2, 1)
    assert (summary["no_match_correct"], summary["no_condition"]) == (1, 2)
    assert summary["failed_attempts"] == 0


def test_failed_attempts_count_as_misses_and_are_reported() -> None:
    summary = score([_result(("gout",), ("gout",), status="timeout"), _result((), (), status="refused")])

    assert summary["top3_hit"] == 0
    assert summary["no_match_correct"] == 0
    assert summary["failed_attempts"] == 2
    assert summary["failed_by_status"] == {"refused": 1, "timeout": 1}

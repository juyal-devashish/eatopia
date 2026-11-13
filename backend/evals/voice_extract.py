"""Voice extraction eval: synthetic things a member might say on each voice screen, with the answers we'd accept.

Every covered question in every case is scored as one of:
- filled correctly: the answer we expected (any order for several options; any words for "own words");
- filled wrongly: a different answer to something the member did say (the costly error: it looks done);
- invented: an answer to something the member never mentioned;
- missed: left empty although the member said it (costs the member one tap);
- correctly empty: left empty because the member didn't say it.
Answers go through the same checks as the endpoint (`checked_answers`): invalid ids and words the member never
said are dropped before scoring. Refusals, timeouts, errors and parse failures count as failed attempts.

    uv run python -m evals.voice_extract            # dry run with the offline stand-in, free
    uv run python -m evals.voice_extract --live     # real Claude calls: one per case (30), costs money
"""

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.catalog import load_catalog
from app.claude_client import (
    AnthropicTransport,
    CatalogRef,
    MemberText,
    ModelTransport,
    build_extract_request,
    call_model,
    parse_extract,
)
from app.config import Settings
from app.main import checked_answers, voice_questions
from app.offline_model import OfflineTransport
from app.questions import load_schema

HERE = Path(__file__).parent
CASES = HERE / "voice_extract_cases.jsonl"
RESULTS = HERE / "results"
OWN_WORDS = "<own words>"
OUTCOMES = ("correct", "wrong", "invented", "missed", "empty")


@dataclass(frozen=True)
class Case:
    id: str
    screen: str
    text: str
    expected: dict[str, Any]


@dataclass(frozen=True)
class CaseResult:
    case: Case
    status: str
    answers: dict[str, Any]


def load_cases(path: Path = CASES) -> list[Case]:
    return [
        Case(id=raw["id"], screen=raw["screen"], text=raw["text"], expected=raw["expected"])
        for raw in (json.loads(line) for line in path.read_text().splitlines())
    ]


def _matches(expected: Any, got: Any) -> bool:
    if expected == OWN_WORDS:
        return isinstance(got, str) and bool(got)
    if isinstance(expected, list) and isinstance(got, list):
        return set(expected) == set(got)
    return bool(expected == got)


def judge(expected: Any, got: Any) -> str:
    """One question's outcome. `{"any_of": [...]}` accepts several answers, including null."""
    accepted = expected["any_of"] if isinstance(expected, dict) and "any_of" in expected else [expected]
    if got is None:
        return "empty" if None in accepted else "missed"
    if any(a is not None and _matches(a, got) for a in accepted):
        return "correct"
    return "invented" if accepted == [None] else "wrong"


def score(results: list[CaseResult]) -> dict[str, Any]:
    counts = dict.fromkeys(OUTCOMES, 0)
    for r in results:
        for question, expected in r.case.expected.items():
            got = r.answers.get(question) if r.status == "ok" else None
            counts[judge(expected, got)] += 1
    said = counts["correct"] + counts["wrong"] + counts["missed"]
    filled = counts["correct"] + counts["wrong"] + counts["invented"]

    def rate(n: int, d: int) -> float | None:
        return round(n / d, 3) if d else None

    return {
        "cases": len(results),
        "questions": sum(counts.values()),
        "failed_attempts": sum(1 for r in results if r.status != "ok"),
        **counts,
        "said": said,
        "filled_correctly_rate": rate(counts["correct"], said),
        "bad_fill_rate": rate(counts["wrong"] + counts["invented"], filled),
    }


async def run(
    transport: ModelTransport, settings: Settings, cases: list[Case], concurrency: int = 4
) -> list[CaseResult]:
    schema = load_schema()
    screens = {s.id: s for s in schema.screens}
    catalog = CatalogRef.from_catalog(load_catalog())
    gate = asyncio.Semaphore(concurrency)

    async def one(case: Case) -> CaseResult:
        screen = screens[case.screen]
        said = MemberText.from_member(case.text, settings.llm.max_voice_chars)
        questions = voice_questions(screen, screens)
        request = build_extract_request(said, questions, catalog, settings.llm)

        def parse(response: dict[str, Any]) -> dict[str, Any]:
            return checked_answers(parse_extract(response, questions, catalog), screen, screens, said)

        async with gate:
            outcome = await call_model(transport, request, parse, settings.llm)
        return CaseResult(case=case, status=outcome.status, answers=outcome.result or {})

    return list(await asyncio.gather(*(one(case) for case in cases)))


def report(summary: dict[str, Any], label: str) -> str:
    def pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    s = summary
    return "\n".join(
        [
            f"Voice extraction ({label}): {s['cases']} cases, {s['questions']} questions",
            f"  filled correctly:       {s['correct']}/{s['said']} said ({pct(s['filled_correctly_rate'])})",
            f"  filled wrongly:         {s['wrong']}",
            f"  invented:               {s['invented']}",
            f"  bad fills:              {s['wrong'] + s['invented']} of all fills ({pct(s['bad_fill_rate'])})",
            f"  missed (one tap each):  {s['missed']}",
            f"  correctly left empty:   {s['empty']}",
            f"  failed attempts:        {s['failed_attempts']}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--live", action="store_true", help="call Claude (costs money); default is the offline stand-in"
    )
    parser.add_argument("--model", help="model to evaluate instead of the configured one (LlmSettings.model)")
    args = parser.parse_args()

    settings = Settings()
    if args.model:
        settings.llm = settings.llm.model_copy(update={"model": args.model})
    transport: ModelTransport = (
        AnthropicTransport(settings.llm, settings.anthropic_api_key) if args.live else OfflineTransport()
    )
    label = f"live, {settings.llm.model}" if args.live else "offline stand-in, dry run"
    results = asyncio.run(run(transport, settings, load_cases()))
    summary = score(results)
    print(report(summary, label))

    if args.live:
        RESULTS.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out = RESULTS / f"voice_extract_{settings.llm.model}_{stamp}.json"
        cases = [
            {
                "id": r.case.id,
                "text": r.case.text,
                "expected": r.case.expected,
                "status": r.status,
                "answers": r.answers,
            }
            for r in results
        ]
        payload = {"model": settings.llm.model, "effort": settings.llm.match_effort, "summary": summary, "cases": cases}
        out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Saved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()

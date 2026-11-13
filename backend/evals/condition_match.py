"""Condition-matching eval: synthetic phrasings, each with the conditions we'd accept (or none).

Reported the way Eatopia reports food matching ("81% of 679 foods matched"):
- top-3 hit: an accepted condition is among the suggestions;
- top-1: the first suggestion is an accepted one;
- wrong first suggestion: the first suggestion is not an accepted one;
- correct "no match": nothing suggested when nothing on the list fits.
Refusals, timeouts, errors and parse failures are counted as failed attempts and as misses, never dropped.

    uv run python -m evals.condition_match            # dry run with the offline matcher, free
    uv run python -m evals.condition_match --live     # real Claude calls: one per case, costs money
    uv run python -m evals.condition_match --live --model claude-sonnet-5-5   # another model, same cases
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
    build_match_request,
    call_model,
)
from app.config import Settings
from app.offline_model import OfflineTransport

HERE = Path(__file__).parent
CASES = HERE / "condition_match_cases.jsonl"
RESULTS = HERE / "results"


@dataclass(frozen=True)
class Case:
    id: str
    text: str
    expected: tuple[str, ...]


@dataclass(frozen=True)
class CaseResult:
    case: Case
    status: str
    matches: tuple[str, ...]


def load_cases(path: Path = CASES) -> list[Case]:
    cases = []
    for line in path.read_text().splitlines():
        raw = json.loads(line)
        cases.append(Case(id=raw["id"], text=raw["text"], expected=tuple(raw["expected"])))
    return cases


def score(results: list[CaseResult]) -> dict[str, Any]:
    with_condition = [r for r in results if r.case.expected]
    no_condition = [r for r in results if not r.case.expected]

    def ok(r: CaseResult) -> bool:
        return r.status == "ok"

    top1 = sum(1 for r in with_condition if ok(r) and r.matches[:1] and r.matches[0] in r.case.expected)
    top3 = sum(1 for r in with_condition if ok(r) and set(r.matches[:3]) & set(r.case.expected))
    wrong_first = sum(1 for r in with_condition if ok(r) and r.matches and r.matches[0] not in r.case.expected)
    none_correct = sum(1 for r in no_condition if ok(r) and not r.matches)

    def rate(n: int, d: int) -> float | None:
        return round(n / d, 3) if d else None

    return {
        "cases": len(results),
        "failed_attempts": sum(1 for r in results if not ok(r)),
        "failed_by_status": {
            s: sum(1 for r in results if r.status == s) for s in sorted({r.status for r in results} - {"ok"})
        },
        "with_condition": len(with_condition),
        "top3_hit": top3,
        "top3_hit_rate": rate(top3, len(with_condition)),
        "top1_correct": top1,
        "top1_rate": rate(top1, len(with_condition)),
        "wrong_first_suggestion": wrong_first,
        "wrong_first_rate": rate(wrong_first, len(with_condition)),
        "no_condition": len(no_condition),
        "no_match_correct": none_correct,
        "no_match_rate": rate(none_correct, len(no_condition)),
    }


async def run(
    transport: ModelTransport, settings: Settings, cases: list[Case], concurrency: int = 4
) -> list[CaseResult]:
    catalog = CatalogRef.from_catalog(load_catalog())
    gate = asyncio.Semaphore(concurrency)

    async def one(case: Case) -> CaseResult:
        request = build_match_request(
            MemberText.from_member(case.text, settings.llm.max_member_chars), catalog, settings.llm
        )
        async with gate:
            outcome = await call_model(transport, request, catalog, settings.llm)
        matches = tuple(m["id"] for m in (outcome.result or {}).get("matches", []))
        return CaseResult(case=case, status=outcome.status, matches=matches)

    return list(await asyncio.gather(*(one(case) for case in cases)))


def report(summary: dict[str, Any], label: str) -> str:
    def pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    def line(name: str, count: int, of: int, value: float | None) -> str:
        return f"  {name:<24}{count}/{of} ({pct(value)})"

    s, d = summary, summary["with_condition"]
    return "\n".join(
        [
            f"Condition matching ({label}): {s['cases']} cases",
            line("top-3 hit:", s["top3_hit"], d, s["top3_hit_rate"]),
            line("top-1 correct:", s["top1_correct"], d, s["top1_rate"]),
            line("wrong first suggestion:", s["wrong_first_suggestion"], d, s["wrong_first_rate"]),
            line("correct 'no match':", s["no_match_correct"], s["no_condition"], s["no_match_rate"]),
            f"  {'failed attempts:':<24}{s['failed_attempts']} {s['failed_by_status'] or ''}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="call Claude (costs money); default is the offline matcher")
    parser.add_argument("--model", help="model to evaluate instead of the configured one (LlmSettings.model)")
    args = parser.parse_args()

    settings = Settings()
    if args.model:
        settings.llm = settings.llm.model_copy(update={"model": args.model})
    cases = load_cases()
    transport: ModelTransport = (
        AnthropicTransport(settings.llm, settings.anthropic_api_key) if args.live else OfflineTransport()
    )
    label = f"live, {settings.llm.model}" if args.live else "offline keyword matcher, dry run"
    results = asyncio.run(run(transport, settings, cases))
    summary = score(results)
    print(report(summary, label))

    if args.live:
        RESULTS.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out = RESULTS / f"condition_match_{settings.llm.model}_{stamp}.json"
        out.write_text(
            json.dumps(
                {
                    "model": settings.llm.model,
                    "effort": settings.llm.match_effort,
                    "summary": summary,
                    "cases": [
                        {
                            "id": r.case.id,
                            "text": r.case.text,
                            "expected": r.case.expected,
                            "status": r.status,
                            "matches": r.matches,
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        print(f"Saved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()

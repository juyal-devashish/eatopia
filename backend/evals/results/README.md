# Eval results

Live runs are kept here. The phrasings are synthetic; each file holds the model, the summary and every answer.

## Voice extraction

What the member says on a voice screen, turned into answers (`evals/voice_extract.py`, 30 transcripts, 150
questions). Each answer is filled correctly, filled wrongly, invented (filled though never mentioned), missed (left
for the member to tap), or correctly left empty.

| Date | Model, effort | Filled correctly | Wrong | Invented | Missed | Correctly empty | Failed |
|---|---|---|---|---|---|---|---|
| (dry run) | offline keyword stand-in | 32/68 | 4 | 2 | 32 | 80 | 0 |

No live run yet (30 calls).

## Condition matching

| Date | Model, effort | Cases | Top-3 hit | Top-1 | Wrong first | Correct "no match" | Failed |
|---|---|---|---|---|---|---|---|
| 2026-11-13 | claude-sonnet-5-5, low | 52 | 45/45 | 45/45 | 0/45 | 7/7 | 0 |
| (dry run) | offline keyword matcher | 52 | 13/45 | 9/45 | 9/45 | 6/7 | 0 |

**Read with care.** The 52 phrasings are written by us and mostly clear-cut, and ambiguous ones accept several
conditions. A perfect score on this set says the matcher handles plain descriptions, not that it is perfect. In 5
cases the model added a reasonable second or third suggestion beyond the accepted list (for example insulin resistance
alongside PCOS); the scoring doesn't penalise extras. Harder cases (vague, misspelled, several conditions at once,
other languages) are the next step before quoting a number.

# Health-first onboarding

**Live demo: https://eatopia-demo.vercel.app** (synthetic data only; best on a phone)

A nutrition app's onboarding asks for Apple Health access in its third section, after the member has already typed
five answers Health could have given, and then asks two more by hand. This demo moves the permission to the start
and turns Health data into **answers the member confirms**: five facts on one review card, two estimates shown as
hints. Plain code does that mapping; the model never sees a Health value. Claude is used only where free text helps:
matching "my sugar was high at my last check-up" to a condition list, and writing a short note for the dietitian.

Built as a work sample for Eatopia. Not affiliated with Eatopia: the look follows its design language, but no logo,
name, copy or screenshots of its app are used. Synthetic data only, no real member data.

## Try it in two minutes

1. Tap **Start onboarding**. You go through as a synthetic member whose watch has recorded everything.
2. Allow the simulated Apple Health access, check the answers it filled in, and tap through the rest.
3. The finish screen compares your screens and taps with the same questions asked one per screen.
4. Open **See what the dietitian gets**: a summary, then every answer marked *from Health, confirmed*, *changed* or
   *entered by member*.
5. On a laptop, **Behind the scenes** sits beside the app (on a phone, tap **Details**): the member's Health data,
   what each rule did, and every request sent to the model, word for word.

## What was measured

| | |
|---|---|
| Screens and taps | 22 screens with 5 answers filled from Health and 2 suggested, against 25 screens and at least 45 taps for the same questions one per screen |
| Condition matching (Claude Sonnet 5.5) | 45/45 right condition in the top 3 and first; 7/7 correctly "no match", including a prompt injection; 52 synthetic phrasings ([results](backend/evals/results/README.md)) |
| Keyword baseline on the same set | 13/45 in the top 3 |
| Live model calls | about 3 s each (2.6 s match, 3.6 s summary; one live check each) |

The matching set is written by us and mostly clear-cut, so read 45/45 as "handles plain descriptions", not "never
misses". Harder phrasings are the next step.

## The one request an iPhone app would send

The web demo can't read HealthKit, so the server builds the summary a phone would send, from synthetic HealthKit
samples. A real app sends this after reading HealthKit, and nothing else changes:

```http
POST /sessions/{id}/health-summary
```

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-13T15:30:00Z",
  "read_types_with_data": ["HKQuantityTypeIdentifierBodyMass", "HKQuantityTypeIdentifierStepCount", "..."],
  "biological_sex": "female",
  "date_of_birth": "1990-03-14",
  "latest_height": { "value": 1.6834, "unit": "m", "at": "2025-09-29T08:00:00Z", "source": "iPhone (synthetic)" },
  "latest_weight": { "value": 73.417, "unit": "kg", "at": "2026-11-10T08:00:00Z", "source": "Smart scale (synthetic)" },
  "workouts_last_28d": 22,
  "workouts_recorded": 25,
  "daily_steps_30d": [{ "day": "2026-10-14", "count": 10250 }, "... one entry per day with data"]
}
```

Seven rules in [`backend/app/rules.py`](backend/app/rules.py) turn it into suggestions. Weak data is asked, never
estimated: weight older than 90 days, fewer than 14 days of steps, or no workout ever recorded (which can't be told
apart from "doesn't log workouts").

## The privacy test

No Health value reaches the model. Three things hold that in place:

- [`backend/app/claude_client.py`](backend/app/claude_client.py) is the only code that calls Claude. Its functions
  take member-typed text (emails, links, dates and long numbers removed) and our condition list; a test checks
  their signatures and that the module imports nothing from the Health, rules or database code.
- The dietitian summary gets the member's answers to questions that aren't Health-linked, plus placeholder names
  like `{{weight}}`. Code fills those in afterwards.
- [`backend/tests/test_canary.py`](backend/tests/test_canary.py) gives each synthetic member unique marker values
  (for example 73.417 kg), runs every member through both orders calling every model endpoint, and fails if a
  marker or any value derived from it appears in anything sent. Seeding a marker into the typed text makes it fail.

```bash
cd backend && uv run pytest tests/test_canary.py
```

## Built like a production service

- **Retries are safe.** Every answer and model call carries a key: a retried request returns the stored result and
  never saves twice or calls the model twice. A reloaded page resumes where it left off.
- **Model calls don't block** other members (async client, timeouts), and refusals, timeouts and parse failures
  are recorded, not dropped.
- **Costs are capped**: 5 model calls a session, 300 a day, 20 new sessions an hour per address.
- **Tests never call a paid API.** More than 160 backend tests (real Postgres, a fake model) and 43 Playwright runs on desktop
  and phone sizes with accessibility scans, using a labelled offline stand-in for the model.

## Stack

| | |
|---|---|
| Web | Next.js (App Router, TypeScript strict), on Vercel |
| API | FastAPI, SQLAlchemy, Alembic, Postgres, on Railway ([`.railway/railway.ts`](.railway/railway.ts)) |
| Model | Claude Sonnet 5.5, structured outputs limited to the listed options |

## Run it locally

Needs Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22 and Postgres.

```bash
createdb intake && createdb intake_test && createdb intake_e2e
```

```bash
make migrate && make backend-dev
```

```bash
make web-dev
```

`LLM_TRANSPORT=offline` runs without an API key. `make check` runs lint, types and tests; `make e2e` runs Playwright.
The plan and its decisions are in [`docs/plan-health-prefill.md`](docs/plan-health-prefill.md).

## Limits

- The iPhone side is simulated; the Health permission sheet is labelled as such.
- Onboarding sections 5 to 7 (food, kitchen, last details) are an assumed, typical intake.
- Sessions are anonymous and deleted after 24 hours.

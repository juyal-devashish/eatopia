# Health first, then voice: a 7-screen onboarding

**Live demo: https://eatopia-demo.vercel.app** (synthetic data only; best on a phone)

A nutrition app's onboarding asks about 25 screens of questions, and asks for Apple Health access only in its third
section, after the member has already typed answers Health could have given. This demo asks the same questions in
**7 screens**, so the member does far less work:

| | One question per screen | This demo |
|---|---|---|
| Screens | 25 | 7 |
| Taps | at least 45 | 13 or 14 when every answer is heard (2 or 3 more for each one the member chooses) |
| Answers filled for you | 0 | up to 22 of 23, each one confirmed by the member |

1. **Apple Health first.** Plain code turns Health data into seven answers on one card: five facts filled in
   (sex at birth, date of birth, height, weight, daily steps) and two estimates the member taps to accept (exercise,
   activity). The model never sees a Health value.
2. **Then three voice prompts.** The member says a few sentences ("I want more energy, my doctor mentioned
   prediabetes, I'm vegetarian and dairy upsets me…") and Claude fills the remaining questions from them, limited to
   each question's own options. The member confirms, changes or chooses each answer on the same screen.

Gender identity is the one question asked on its own: it is never inferred, by code or by the model.

Built as a work sample for Eatopia. Not affiliated with Eatopia: the look follows its design language, but no logo,
name, copy or screenshots of its app are used. Synthetic data only, no real member data.

## Try it in two minutes

1. Tap **Start onboarding**. You go through as a synthetic member whose watch has recorded everything.
2. Allow the simulated Apple Health access, then check the seven answers it filled in.
3. Pick an answer for gender.
4. On each voice screen, tap the mic. The synthetic member's words appear, then the answers they fill in. Change any
   of them, or clear the text and type your own words to see Claude fill the form from them.
5. The finish screen compares your screens and taps with the same questions asked one per screen.
6. **See what the dietitian gets**: a short note, then every answer marked *from Health, confirmed*, *changed*,
   *from what they said, confirmed* or *entered by member*.
7. On a laptop, **Behind the scenes** sits beside the app (on a phone, tap **Details**): the member's Health data,
   what each rule did, and every request sent to the model, word for word.

The microphone is simulated: the web demo can't rely on browser speech recognition, which fails silently inside
the in-app browsers many links open in. On an iPhone, on-device dictation would send only the text, to the same
endpoint the demo uses.

## How it works

```
iPhone (simulated)          API (FastAPI, Postgres)                        Claude
HealthKit ─ summary ──────▶ rules (plain code) ─▶ 7 suggestions
                            Health card: member confirms
dictation ─ text only ────▶ /screens/{id}/extract ───────────────────────▶ member's words + our question
                            re-check every answer ◀─────────────────────── and option lists only
                            voice screen: member confirms
                            dietitian note ──────────────────────────────▶ member's answers, never a Health value
```

### The two requests an iPhone app would send

After reading HealthKit, one summary:

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

Seven rules in [`backend/app/rules.py`](backend/app/rules.py) turn it into suggestions, with thresholds in config.
Weak data is asked, never estimated: weight older than 90 days, fewer than 14 days of steps, or no workout ever
recorded (which can't be told apart from "doesn't log workouts").

Then, on each voice screen, the transcript:

```http
POST /sessions/{id}/screens/voice_food/extract
{ "text": "I'm vegetarian. Lactose upsets my stomach…", "request_key": "…" }
```

The reply holds one answer per question the screen covers, or `null` when it wasn't mentioned. Structured output
limits each answer to that question's listed options (or our condition list), and the server checks every answer
again: invalid ones are dropped, and so are "own words" (medications, foods to avoid) that the member didn't
actually say. A matched health condition is shown as a suggestion that needs its own tap.

## What was measured

| | |
|---|---|
| Screens and taps | 7 screens, against 25 screens and at least 45 taps for the same questions one per screen (the baseline is computed from the question list in [`backend/app/baseline.py`](backend/app/baseline.py)) |
| Voice extraction | 30 synthetic transcripts, 150 answers, each scored as filled correctly, filled wrongly, invented, missed or correctly empty. The free dry run with a keyword stand-in fills 32 of 68 spoken answers correctly. **The live run with Claude hasn't been made yet** ([results](backend/evals/results/README.md)) |
| Condition matching | 45/45 right condition first and 7/7 correctly "no match" (Claude Sonnet 5.5, 52 synthetic phrasings). This was the earlier version's concern screen; voice extraction now picks the condition from the same list |
| Live model calls | about 3 s each (3.2 s for a voice screen, 3.6 s for the dietitian note; one live check each) |

The eval sets are written by us and mostly clear-cut, so read the scores as "handles plain descriptions", not
"never misses".

## The privacy test

No Health value reaches the model. Three things hold that in place:

- [`backend/app/claude_client.py`](backend/app/claude_client.py) is the only code that calls Claude. Its functions
  take what the member typed or said (emails, links, dates and long numbers removed) and our own question, option
  and condition lists. A test checks their signatures and that the module imports nothing from the Health, rules or
  database code.
- The dietitian note gets the member's answers to questions that aren't Health-linked, plus placeholder names like
  `{{weight}}`. Code fills those in afterwards.
- [`backend/tests/test_canary.py`](backend/tests/test_canary.py) gives each synthetic member unique marker values
  (for example 73.417 kg), runs every member through every flow calling every model endpoint, and fails if a marker
  or any value derived from it appears in anything sent.

```bash
cd backend && uv run pytest tests/test_canary.py
```

## Built like a production service

- **Retries are safe.** Every answer and model call carries a key: a retried request returns the stored result and
  never saves twice or calls the model twice. A reloaded page resumes where it left off.
- **Model calls don't block** other members (async client, timeouts), and refusals, timeouts and parse failures
  are recorded, not dropped. When a call fails, the voice screen simply asks each question.
- **Costs are capped**: 8 model calls a session, 300 a day, 20 new sessions an hour per address.
- **Tests never call a paid API.** 188 backend tests (real Postgres, a fake model) and 37 Playwright runs on desktop
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
make migrate && make backend-dev     # API on http://localhost:8000
make web-dev                         # web app on http://localhost:3000
```

`LLM_TRANSPORT=offline` runs without an API key, using a keyword stand-in for Claude. `make check` runs lint, types
and tests; `make e2e` runs Playwright.

| Doc | What's in it |
|---|---|
| [`docs/plan-voice-intake.md`](docs/plan-voice-intake.md) | The current demo: one scenario, Health first, then voice |
| [`docs/plan-health-prefill.md`](docs/plan-health-prefill.md) | Architecture, the Health rules, the privacy rules, reliability |
| [`docs/plan-m8-deploy.md`](docs/plan-m8-deploy.md) | How it's deployed |

## Limits

- The iPhone side is simulated: the Health permission sheet and the microphone are labelled as such.
- One synthetic member is shown. The backend also has a member with gaps in their data and one with none, and its
  tests cover them (old weight and missing workouts are asked, never guessed).
- Onboarding sections 5 to 7 (food, kitchen, last details) are an assumed, typical intake.
- Sessions are anonymous and deleted after 24 hours.

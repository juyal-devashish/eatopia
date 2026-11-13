# Plan: Health-prefilled onboarding (v5, draft)

Status: **draft for discussion, not final.** The Health MCP server is deferred (see "Later"). Everything is built in
Eatopia's own stack. `PLAN.md` holds the earlier research and the privacy rules this plan depends on.

## The pitch

Eatopia asks for Apple Health access in section 3 of onboarding, after the member has already typed in five answers
Health could have given. After access is granted, it still asks two more, with nothing preselected (confirmed on a
real run: every answer was tapped by hand). This demo moves the permission to the start,
prefills those seven answers as **suggestions the member confirms**, and uses Claude only where free text helps
(matching a condition, mapping "Something else"). No Health value ever reaches the model, which keeps their own rule.

It ships as **a web app shaped like a phone**: one link, nothing to install, works on a laptop or a phone.

## Their stack, and what we use from it

| Layer | Theirs (source) | In this demo |
|---|---|---|
| Web app | Next.js App Router on Railway (eatopia.ai and app.eatopia.ai, checked 2026-11-13) | Next.js App Router, TypeScript strict, on Railway |
| Backend | FastAPI + Postgres on Railway (privacy policy, Hongkun's profile) | FastAPI + Postgres on Railway |
| AI | Claude via the Anthropic API (privacy policy) | Anthropic Python SDK, one backend module |
| Errors | Sentry (privacy policy) | Sentry on web and backend |
| iPhone app | Native iOS with HealthKit | Not built. The web app simulates it; the iPhone's part is one documented request (see "The HealthKit contract") |
| Not needed | Stripe, IAP, Resend, Twilio | Not used |

Open: their ORM, migration tool and CSS approach. Defaults: SQLAlchemy 2 + Alembic, Tailwind. Switch if we learn otherwise.

## Onboarding today (from screenshots, 2026-11-13)

Seven sections on the progress bar. The screenshots cover the first four; sections 5–7 weren't captured, so the demo
uses a typical intake for them (marked *assumed* below). No personal values are recorded here.

| Section | Question | Health can answer? |
|---|---|---|
| Your goals | What would you like to change first? | No |
| About you | How do you describe yourself? | No |
| About you | What sex were you assigned at birth? | Yes: `biologicalSex` |
| About you | When were you born? | Yes: `dateOfBirth` |
| About you | What is your height? | Yes: height samples |
| About you | What is your current weight? | Yes: body mass samples |
| About you | Anything about your weight to work on? | No |
| About you | How often do you exercise? | Yes: workouts |
| Your routine | *Apple Health permission (steps, workouts, weight, sleep)* | |
| Your routine | How many times do you usually eat in a day? | No |
| Your routine | How much are you on your feet? | Partly: derived from steps |
| Your routine | About how many steps on most days? | Yes: step count |
| Your health | One health concern you'd most like help with? (123 conditions) | No, but free text helps |
| Your health | What makes healthy eating hard? | No |
| *Your food (assumed)* | Which best describes how you eat? (no restrictions, vegetarian, vegan, pescatarian, halal, kosher, something else) | No |
| *Your food (assumed)* | Any food allergies or intolerances? (multi-select) | No |
| *Your food (assumed)* | Any foods you'd rather avoid? (optional) | No |
| *Your food (assumed)* | Which cuisines feel like home? (multi-select) | No |
| *Your kitchen (assumed)* | Who does most of the cooking? | No |
| *Your kitchen (assumed)* | How much time do you have for a weeknight dinner? | No |
| *Your kitchen (assumed)* | How does your weekly food budget feel? | No |
| *Your kitchen (assumed)* | How often do you eat out or order in? | No |
| *Last details (assumed)* | Any medications or supplements? (free text, "Add this later") | Not in this build: needs clinical records |
| *Last details (assumed)* | Anything else your dietitian should know? (optional free text) | No |

7 of 24 questions can be suggested from Health, and all 7 sit in the sections we saw. Their permission sheet asks for steps, workouts, weight and sleep;
prefilling also needs height, date of birth and biological sex, which are separate HealthKit read types.

## Rules we keep (theirs, from `PLAN.md`)

1. Device data never goes to the language model, enforced by a test.
2. Glucose is not shown to the member and never changes anything automatically. (Out of scope here.)
3. The model does no clinical math. All Health-to-answer mapping is plain code.
4. Identifiers are stripped before any text goes to the model.
5. Cycle data stays out of scope.

Ours: synthetic data only, labelled as synthetic on screen; our own visual design, with no Eatopia branding, screens,
colours or copy (the repo and the link are public); nothing is saved as an answer until the member confirms it.

## What a visitor sees

**Desktop:** a phone frame in the middle of the page and a "Behind the scenes" panel beside it.
**Phone:** the frame drops away and the onboarding fills the screen; the panel moves behind a button.

1. **Start screen** (outside the phone): pick a synthetic member (A, B or C) and a mode:
   - **Today's order:** the current flow, Health permission in section 3, every question asked.
   - **Health first:** the new flow.
2. **Inside the phone:** one question per screen with tap-to-answer options and a progress bar, like a real app.
3. **Health first mode:**
   - A simulated permission sheet, clearly marked "Simulated: Apple Health", appears before "About you".
   - Answers Health can give are preselected with a source line, for example *"From Apple Health · 30-day average"*,
     and a **Looks right** button. Tapping another option records an edit.
   - Weak or missing data is never guessed: the question appears unselected, as today.
4. **Your health:** the member can type the concern in a sentence. Claude suggests up to three matches from the
   condition list; the member taps one, or opens the full list.
5. **Finish screen:** time taken, taps and questions answered in this run. After trying both modes, it shows them side
   by side: *"Your run: Today's order 2m 10s, 24 taps · Health first 58s, 11 taps."* (Example numbers only; the real
   ones come from the visitor's own runs.)
6. **Dietitian view** (button on the finish screen): the intake record, each answer marked `from Health, confirmed`,
   `from Health, changed` or `entered by member`, plus the model-call log.

**Behind the scenes panel**, updated live:
- the Health summary for this member (the member's own values, which is fine to show them);
- which rule produced each suggestion, and why a question was left unselected;
- **What the model saw:** every request sent to Claude, word for word.

## Architecture

```
Browser (Next.js on Railway)               API (FastAPI on Railway)                    Anthropic API
start screen ─ pick member, mode ────────▶ POST /sessions
                                           synthetic HealthKit fixtures
                                             └▶ summary builder (stands in for the iPhone)
                                                 └▶ health_summary (device class)
                                           mapping rules ─▶ suggestions
phone frame screens ◀───────────────────── GET /sessions/{id}/form
taps, confirms, edits ───────────────────▶ POST /sessions/{id}/answers
condition free text ─────────────────────▶ POST /sessions/{id}/conditions/match ─▶ claude_client ─▶ Claude
                                                                                (member text + catalog only)
finish, dietitian view ◀────────────────── GET /sessions/{id}/record, /egress
                                           Postgres
```

### The HealthKit contract

The web app can't read HealthKit, so the backend builds the same summary an iPhone would send, from synthetic
HealthKit-shaped samples (type identifier, value, unit, start, end, source). The summary is a versioned schema,
`HealthSummaryV1`: latest height, latest weight and its date, date of birth, biological sex, 28-day workout count,
30-day daily step series, and which read types returned data. A real iOS app would send exactly this with
`POST /sessions/{id}/health-summary`. The plan names this endpoint as the only change their app would need.

Fixture dates are stored as offsets from "now" ("weight: 3 days ago"), so the demo never goes stale. Tests inject a
fixed clock.

### Backend (FastAPI)

- **Endpoints:** `POST /sessions`, `GET /sessions/{id}/form`, `POST /sessions/{id}/health-summary`,
  `POST /sessions/{id}/answers`, `POST /sessions/{id}/conditions/match`, `POST /sessions/{id}/complete`,
  `GET /sessions/{id}/record`, `GET /sessions/{id}/egress`.
- **Tables:** `intake_session` (member, mode, started and finished times, tap count); `health_summary` (every field
  tagged `device`); `intake_answer` (value, source, provenance, rule id and version, confirmed_at);
  `condition_catalog`; `llm_call` (exact request and response, status: ok, refused, timeout, parse_failed).
- **Question schema:** one JSON file (sections, questions, option ids, which rule can answer each, and where the
  Health permission sits in each mode). The web app renders whatever `/form` returns.
- Sessions are anonymous and deleted after 24 hours.

### Mapping rules (plain code, thresholds in config)

| Question | Rule | Leave unselected when |
|---|---|---|
| Sex at birth | `biologicalSex` female/male → option | not set or "other" |
| Date of birth | `dateOfBirth` → picker | not set |
| Height | latest height sample | none |
| Weight | latest sample ≤ 30 days → preselect; 31–90 days → preselect and mark "please check" | none, or older than 90 days |
| Exercise | workouts in last 28 days ÷ 4 → their buckets | **no workout ever recorded** (can't tell "doesn't exercise" from "doesn't log") |
| Steps | median of days with data over 30 days → their buckets | fewer than 14 days with data |
| On your feet | from the same step median (under 5,000 sedentary; 5,000–7,499 lightly; 7,500–9,999 moderately; 10,000+ very active), labelled "suggested from your steps" | the steps rule left it unselected |

Every suggestion carries its source, date range and rule id.

### Where Claude is used

Only in `backend/app/claude_client.py`. Model, effort and limits come from config.

1. **Condition matching.** Input: the member's sentence (identifiers stripped, 300 characters max) and the condition
   catalog. Output: structured JSON whose condition ids are an **enum of catalog ids**, so the model can't invent a
   condition; the backend re-checks every id anyway.
2. **"Something else" answers.** Map a free-text answer to existing options (diet, allergies, barriers), or keep it
   as the member's own words. Medications and "anything else" are stored verbatim and only reach the model inside the
   dietitian summary, with identifiers stripped.
3. **Dietitian summary.** The model gets member-entered answers and field names only, and writes `{{weight}}`-style
   placeholders; the backend fills in the Health values.

Defaults: `claude-opus-5-5`, low effort for matching and medium for the summary, structured outputs, and the API's
server-side refusal fallback turned on. Refusals, timeouts and parse failures are stored as failed attempts.

**Cost guard (the link is public):** at most 5 model calls per session and a daily cap from config. When a cap is
hit, matching falls back to the full condition list and the summary to a template, and the panel says so.

### The privacy firewall

- `claude_client` only accepts `MemberText` and `CatalogRef`. No function in it takes a `HealthSummary`, so passing
  one is a type error (mypy runs in `make check`).
- **Canary test:** each synthetic member has unique marker values (for example 73.417 kg, 4,812 steps). A fake
  Anthropic client records every request; the test fails if any marker appears.
- The "What the model saw" panel and the dietitian view read straight from the `llm_call` log.

### Web app (Next.js)

- App Router, TypeScript strict, server components for the start screen and dietitian view, client components inside
  the phone frame.
- `PhoneFrame` (about 390 × 844, our own design) wraps the onboarding; below about 500 px wide it renders full screen.
- Screens are generated from the question schema: single choice, multiple choice, wheel-style date and number
  pickers, interstitial cards. One component per kind.
- Taps and timings are counted on the client and sent with each answer.
- Use the current stable Next.js and read its docs before writing code; it changes quickly.

## Synthetic members

| Member | Health data | Expected in Health first |
|---|---|---|
| A: wears a watch | everything, recent | 7 of 7 suggested |
| B: phone only | steps with gaps, weight 4 months old, no workouts | some suggested; weight and exercise asked |
| C: no data | nothing (or access denied) | same as today's order |

Plus a short **synthetic** condition catalog we write ourselves (about 40 common conditions), labelled as ours.

## Repo layout

```
eatopia/
  AGENTS.md            rules: synthetic data, firewall, no paid calls in tests, push policy
  Makefile             make check = backend (ruff, mypy, pytest) + web (lint, typecheck, tests)
  backend/             FastAPI app, Alembic, fixtures/, question schema JSON, tests/
  web/                 Next.js app
  docs/                this plan
```

## Tests

- No test calls the network or a paid API. Model responses are recorded fixtures.
- Backend: every mapping rule at its bucket edges and "leave unselected" cases; provenance kept through confirm and
  edit; the canary test; catalog-id validation; caps and fallbacks; failed model calls recorded.
- Web: component tests for each screen kind; one Playwright run per member and mode against a local backend with
  the fake Claude client.
- One small live check of condition matching, about 10 real calls, run only with your OK.

## Milestones (one commit each)

| # | Milestone | Done when |
|---|---|---|
| M0 | Repo setup: `AGENTS.md`, backend and web skeletons, `make check`, GitHub Actions | `make check` passes in CI |
| M1 | Question schema and synthetic HealthKit fixtures | schema served from `/form` |
| M2 | Summary builder, mapping rules, database tables | rule tests pass for A, B and C |
| M3 | `claude_client`, egress log, canary test, cost caps | canary test passes with a fake client |
| M4 | Web: start screen, phone frame, "Today's order" end to end | Playwright run passes for all members |
| M5 | Web: "Health first" with permission sheet, suggestions, confirm and edit, Behind the scenes panel | Playwright run passes for all members |
| M6 | Condition matching and "Something else" | live check passes (≈10 calls) |
| M7 | Finish screen comparison and dietitian view | both render for all members |
| M8 | Deploy to Railway (web, API, Postgres) with Sentry | full flow works on the public link, on laptop and phone |
| M9 | Measure and record | timings, a 60–90 second video, and the note |

Rough size: 5–7 focused days. M5 (the suggestion screens and live panel) carries the most risk.

## What we measure (and quote)

For each synthetic member, both modes: questions shown, taps and time to finish, from our own runs. We quote what
we measure, never "15 minutes to 3".

## Risks and open questions

1. **Sections 5–7 are assumed.** The demo's point is an easier onboarding, not a copy of theirs, so a typical intake
   stands in. The note to them should say the first four sections follow their flow and the rest are illustrative.
2. ~~Was anything prefilled?~~ Settled: nothing was preselected in their app.
3. **It's a simulation of the iPhone side.** We say so on screen, and the HealthKit contract shows the one request
   their app would make.
4. **Looking too much like their app.** Same flow logic, our own design. No screenshots of their app in the repo.
5. **Public link costs.** Covered by the caps; Anthropic usage limits set as a backstop.
6. **They may already plan this.** The pitch leads with "Health access first, suggestions the member confirms",
   which stands either way.

## Later (not in this build)

- **Health MCP server:** wraps the same backend services (summary, rules, coverage) so Sage or the dietitian console
  can use them. The backend keeps those as plain service functions so the server can sit on top.
- A SwiftUI client that sends `HealthSummaryV1` from real HealthKit.
- Uploading a real Apple Health export.
- Clinical records (medications, labs, conditions).

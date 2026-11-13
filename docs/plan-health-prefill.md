# Plan: Health-prefilled onboarding (v7)

Status: **agreed; being built milestone by milestone.** The Health MCP server is deferred (see "Later"). Everything is
built in Eatopia's own stack. `PLAN.md` holds the earlier research and the privacy rules this plan depends on.

## The pitch

Eatopia asks for Apple Health access in section 3 of onboarding, after the member has already typed in five answers
Health could have given. After access is granted, it still asks two more, with nothing preselected (confirmed on a
real run: every answer was tapped by hand). This demo moves the permission to the start,
prefills those seven answers as **suggestions the member confirms**, and uses Claude only where free text helps
(matching a condition, mapping "Something else"). No Health value ever reaches the model, which keeps their own rule.

It follows the same principle as their meal-logging pipeline, where unmatched foods are "excluded, not estimated":
a Health answer comes from data or the question is asked; it is never guessed.

It ships as **a mobile-first web app**: one link, nothing to install. It is built for phones; on a laptop it keeps a
phone's width and proportions in the middle of the page, with no device frame.

## Their stack, and what we use from it

| Layer | Theirs (source) | In this demo |
|---|---|---|
| Web app | Next.js App Router on Railway (eatopia.ai and app.eatopia.ai, checked 2026-11-13) | Next.js App Router, TypeScript strict, on Railway |
| Backend | FastAPI + Postgres on Railway (privacy policy, technical cofounder's profile) | FastAPI + Postgres on Railway |
| AI | Claude via the Anthropic API; Sage answers from member data through 6 read-only tools (profile) | Anthropic Python SDK, one backend module |
| Errors | Sentry (privacy policy) | Not used in the demo (decided 2026-11-13); Railway's logs instead |
| iPhone app | SwiftUI with HealthKit (profile) | Not built. The web app simulates it; the iPhone's part is one documented request (see "The HealthKit contract") |
| Dietitian console | Registered-dietitian console (profile) | A dietitian view page |
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

7 of 23 questions can be suggested from Health, all from the 13 questions we saw. Their permission sheet asks for steps, workouts, weight and sleep;
prefilling also needs height, date of birth and biological sex, which are separate HealthKit read types.

## Rules we keep (theirs, from `PLAN.md`)

1. Device data never goes to the language model, enforced by a test.
2. Glucose is not shown to the member and never changes anything automatically. (Out of scope here.)
3. The model does no clinical math. All Health-to-answer mapping is plain code.
4. Identifiers are stripped before any text goes to the model.
5. Cycle data stays out of scope.

Ours: synthetic data only, labelled as synthetic on screen; our own visual design, with no Eatopia branding, screens,
colours or copy (the repo and the link are public); nothing is saved as an answer until the member confirms it.

## UI rules

1. **Explain the benefit before asking for Health.** A short screen says what connecting gets you ("we'll fill in up
   to 5 answers and suggest 2 more"), then the permission sheet. Apple's guidance is to give context before a permission prompt.
2. **Preselect facts, never estimates.** Facts come straight from Health (height, weight, date of birth, sex at
   birth, steps). Estimates (exercise frequency, time on your feet) are shown as a highlighted suggestion the member
   taps. Preselected answers tend to be accepted unread, so only facts earn one.
3. **One review card for the facts.** All Health facts appear on a single "From Apple Health" card with editable
   rows, not on separate preselected screens. Rows with weak data need their own tap before the card can be
   confirmed, so "confirm all" can't skip them.
4. **Handle weight with care.** Eating disorders are among the conditions Eatopia supports, and weight comes before
   the health questions. Weight keeps "Add this later", and no weight trend appears anywhere in onboarding.
5. **Compare runs honestly.** A second run is always faster because the visitor has learned the questions. Lead with
   counts that learning doesn't change (answers filled for you, taps); show time with that caveat.
6. **Accessibility basics from day one.** Tap targets at least 44 px; option lists announced as single- or
   multi-choice groups; full keyboard use; Back keeps earlier answers; reduced-motion respected; the Behind the
   scenes panel can be collapsed and starts collapsed on phones.

Also: gender identity is never derived from Health's sex field, and condition matches are suggestions the member
taps, never auto-selected. Free text is used only for open answers; closed questions stay as tap targets.

## What a visitor sees

**Phone:** the app fills the screen. **Laptop:** the same app in a phone-width column (430 × 932 at most) in the
middle of the page, with no device frame; the "Behind the scenes" panel sits beside it there, and behind a button
on a phone.

1. **Start screen** (the app's first screen): pick a synthetic member (A, B or C) and a mode:
   - **Today's order:** the current flow, Health permission in section 3, every question asked.
   - **Health first:** the new flow.
2. **Onboarding:** one question per screen with tap-to-answer options and a progress bar, like a real app.
3. **Health first mode:**
   - Before "About you", a benefit screen (*"Connect Apple Health and we'll fill in up to 5 answers and suggest 2 more"*), then a
     simulated permission sheet marked "Simulated: Apple Health".
   - **Review card, "From Apple Health":** height, weight, date of birth, sex at birth and steps, each row with its
     value, source and date (for example *"30-day average · updated today"*), editable in place. Weak rows (weight
     31–90 days old) are flagged and need their own tap before **Confirm** works. Weight offers "Add this later".
     These questions then don't appear again later in the flow.
   - **Estimates keep their own screens:** exercise frequency and time on your feet show the suggested option
     highlighted with *"Suggested from Apple Health"*, not selected. The member taps to choose.
   - Missing data is never guessed: that row is dropped from the card and the question is asked as today.
   - Gender identity is always asked; it is never derived from Health.
4. **Your health:** the member can type the concern in a sentence. Claude suggests up to three matches from the
   condition list; the member taps one, or opens the full list.
5. **Finish screen:** answers filled for you, taps and time for this run. After both modes, they appear side by side,
   counts first: *"Health first: 5 filled for you, 2 suggested, 14 taps · Today's order: 0 filled, 26 taps."* Time is
   shown with a note that second runs are faster because you know the questions. (Example numbers only; the real ones
   come from the visitor's own runs.)
6. **Dietitian view** (button on the finish screen): the intake record, each answer marked `from Health, confirmed`,
   `from Health, changed` or `entered by member`, plus the model-call log.

**Behind the scenes panel**, collapsible (collapsed by default on phones), updated live:
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
onboarding screens ◀────────────────────── GET /form, GET /sessions/{id}
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

- **Endpoints:** `GET /form?mode=`, `POST /sessions`, `GET /sessions/{id}` (state, suggestions, next screen),
  `POST /sessions/{id}/health-summary`, `POST /sessions/{id}/screens/{screen_id}/match` ("Something else" mapping),
  `POST /sessions/{id}/answers`, `POST /sessions/{id}/conditions/match`, `POST /sessions/{id}/complete`,
  `GET /sessions/{id}/record`, `GET /sessions/{id}/egress`.
- **Tables:** `intake_session` (member, mode, started and finished times, tap count); `health_summary` (every field
  tagged `device`); `intake_answer` (value, source, provenance, rule id and version, confirmed_at);
  `llm_call` (exact request and response, status: ok, refused, timeout, parse_failed).
- **Question schema:** one JSON file (sections, questions, option ids, which rule can answer each, and where the
  Health permission sits in each mode). The web app renders whatever `/form` returns.
- Sessions are anonymous and deleted after 24 hours.

### Reliability (lessons from their production)

Their technical cofounder fixed phones losing replies the server had already generated, and model calls blocking
other members. The demo handles both from the start:

- **Answers are saved once.** One row per session and question, written with a client-generated key; a retried
  request updates the same row and never duplicates it.
- **Model calls are keyed.** Condition matching stores its result under the request's key; a retry returns the stored
  result and makes no second paid call.
- **Sessions resume.** `GET /sessions/{id}` returns the answers so far and the next screen, so a reloaded page picks
  up where it left off.
- **Model calls don't block.** `claude_client` uses the async Anthropic client with a timeout.
- Tests: a duplicate answer gives one row; a retried match gives one `llm_call`; a resumed session lands on the right
  screen.

### Mapping rules (plain code, thresholds in config)

| Question | Kind | Rule | Ask as today when |
|---|---|---|---|
| Sex at birth | fact (card) | `biologicalSex` female/male → option | not set or "other" |
| Date of birth | fact (card) | `dateOfBirth` | not set |
| Height | fact (card) | latest height sample | none |
| Weight | fact (card) | latest sample ≤ 30 days; 31–90 days → flagged row needing its own tap | none, or older than 90 days |
| Steps | fact (card) | median of days with data over 30 days → their buckets | fewer than 14 days with data |
| Exercise | estimate (hint) | workouts in last 28 days ÷ 4 → their buckets | **no workout ever recorded** (can't tell "doesn't exercise" from "doesn't log") |
| On your feet | estimate (hint) | from the step median (under 5,000 sedentary; 5,000–7,499 lightly; 7,500–9,999 moderately; 10,000+ very active) | the steps rule had too little data |

Every suggestion carries its kind, source, date range and rule id. Facts go on the review card; estimates are
highlighted, never selected.

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

Defaults: `claude-sonnet-5-5` (chosen after the eval run below; Opus 5.5 was the first default), low effort for matching and medium for the summary, structured outputs, and the API's
server-side refusal fallback turned on. Refusals, timeouts and parse failures are stored as failed attempts.

**Offline stand-in:** `LLM_TRANSPORT=offline` swaps Claude for a keyword matcher, so end-to-end runs never call a
paid API and the demo can run locally without a key. It is never used in production.

**Cost guard (the link is public):** at most 5 model calls per session and a daily cap from config. When a cap is
hit, matching falls back to the full condition list and the summary to a template, and the panel says so.

### The privacy firewall

- `claude_client` only accepts `MemberText` and `CatalogRef`. No public function in it takes a Health type, and it
  imports nothing from the Health, rules, answers or database modules; a test checks both.
- **Canary test:** each synthetic member has unique marker values (for example 73.417 kg, 1.6834 m). A fake
  Anthropic client records every request; the test fails if any marker appears.
- The "What the model saw" panel and the dietitian view read straight from the `llm_call` log.

### Web app (Next.js)

- App Router, TypeScript strict. Screens are client components that load data from the API directly, which keeps
  them clear of Next 16's Cache Components rules; the page itself is a thin server component.
- `AppShell` fills a phone's screen (respecting the safe areas); on wider screens it keeps a phone's width and
  proportions, up to 430 × 932, centred, with no device frame.
- Screens are generated from the question schema: single choice, multiple choice, wheel-style date and number
  pickers, interstitial cards, the benefit screen, the permission sheet and the Health review card. One component
  per kind.
- Accessibility per the UI rules: native radio and checkbox semantics under the styling, visible focus, 44 px
  targets, Back that keeps answers, `prefers-reduced-motion` respected. Checked with an axe scan in Playwright.
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
- **Condition-matching eval**, reported the way they report food matching ("81% of 679 foods matched"): about 50
  synthetic phrasings, each with its expected condition or "no match". We report how often the right condition is
  in the top 3, how often a suggestion is wrong, and how often "no match" is correctly returned. About 50 real calls,
  run only with your OK. First live run (2026-11-13, Claude Sonnet 5.5, low effort): 45/45 top-3, 45/45 top-1,
  7/7 correct "no match", no failures, in 22 seconds. The set is clear-cut, so harder cases come next; see
  `backend/evals/results/README.md`.

## Milestones (one commit each)

| # | Milestone | Done when |
|---|---|---|
| M0 | Repo setup: `AGENTS.md`, backend and web skeletons, `make check`, GitHub Actions | `make check` passes in CI |
| M1 | Question schema and synthetic HealthKit fixtures | schema served from `/form` |
| M2 | Summary builder, mapping rules, database tables, idempotent and resumable sessions | rule and retry tests pass for A, B and C |
| M3 | `claude_client`, egress log, canary test, cost caps, and the condition-match endpoint (its first user) | canary test passes with a fake client |
| M4 | Web: start screen, mobile-first app shell, "Today's order" end to end | Playwright run passes for all members |
| M5 | Web: "Health first" with benefit screen, permission sheet, review card, estimate hints, Behind the scenes panel | Playwright and axe runs pass for all members |
| M6 | "Something else" mapping and the condition-match eval | eval run and reported (≈50 calls, with your OK) |
| M7 | Finish screen comparison, dietitian view and summary (Health values filled in by code) | both render for all members |
| M8 | Deploy to Railway (web, API, Postgres) | full flow works on the public link, on laptop and phone |
| M9 | Measure and record | timings, a 60–90 second video, a README a reviewer can read in five minutes (the link, the one HealthKit request, the firewall test), and the note |

Rough size: 5–7 focused days. M5 (the suggestion screens and live panel) carries the most risk.

## What we measure (and quote)

For each synthetic member, both modes: answers filled for you, questions shown and taps, from our own runs. Time is
measured too, with each mode run first half the time, since a second run is always faster. We quote what we
measure, never "15 minutes to 3".

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

- **Health MCP server:** Sage already answers from member data through 6 read-only tools, so an MCP server would
  expose tools like these in a standard format rather than add a capability. It is not part of the pitch. The backend
  keeps the summary and rules as plain service functions in case it is wanted later.
- A SwiftUI client that sends `HealthSummaryV1` from real HealthKit.
- Uploading a real Apple Health export.
- Clinical records (medications, labs, conditions).

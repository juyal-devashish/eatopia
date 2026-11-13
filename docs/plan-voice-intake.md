# Plan: one scenario, Health first, then voice (M10)

Status: **agreed 2026-11-13; being built on `feat/m10-voice`.** Builds on [plan-health-prefill.md](plan-health-prefill.md),
whose rules all still hold.

## Why

The demo showed two orders and three members, so its point only appeared after two runs. The proof of concept is
simpler: **onboarding takes far fewer touches when Apple Health fills what it can and the member says the rest.**
So the demo shows one run, and the finish screen says what the same questions would have cost one per screen.

## What a visitor sees

1. **Start:** a short explainer ("Independent demo · synthetic data only") and one **Start** button. It runs member A
   (full, recent Health data) in Health first. No member or order picker.
2. **Benefit, then permission** (unchanged).
3. **One Health card with 7 answers.** The 5 facts as today, plus exercise and activity as suggested rows that need
   their own tap (the same mechanism as weak-data rows), so they are never preselected. Their separate screens go.
4. **Gender identity:** one tap, as today. Never inferred, by model or by Health.
5. **Three voice prompts**, each with the topics it covers listed on screen while the member talks:

   | Prompt | Covers |
   |---|---|
   | What would you like help with? | main goal, weight goal, health concern, what makes eating hard, meals a day |
   | How do you eat? | diet, allergies, foods to avoid, cuisines |
   | Your kitchen, and anything else | who cooks, weeknight time, food budget, eating out, medications, anything else |

   After each, the same screen shows **"From what you said"**: clear answers filled in and editable; a condition
   match or a low-confidence answer needs its own tap; anything not mentioned appears inline as the usual tap
   options. One **Confirm** saves them all.
6. **Finish:** this run's screens and taps, with the answers from Apple Health and from what you said, next to
   **what the same questions would have taken one per screen** (see "The baseline"). Dietitian view as today, with a
   new provenance label, *from what you said, confirmed*.

About 7 screens instead of 25.

## Input: speech or typing, Claude fills the form

The Claude API takes text, not audio, so speech becomes text first:

- **Speech to text in the browser** (Web Speech API: Safari on iPhone, Chrome). No new vendor, no cost. Audio is
  handled by the browser's own service (Apple or Google), which the voice screen says in one line.
- **Typing is always available**, and is the path when speech isn't supported (Firefox, some in-app browsers) or
  the member declines the microphone. The rest of the flow is identical: Claude reads the text and fills the form.
- End-to-end tests use the typing path. Speech recognition itself is not tested in CI.

If browser speech proves unreliable on the target phones, the demo stays typing-first with the mic as an extra;
the proof of concept (one sentence instead of many screens) holds either way.

## Backend

- **Schema:** new screen kind `voice` with `covers: [screen ids]`, Health first only. Validation: covered screens
  exist, are not Health-linked, and each is covered at most once. `dietitian_note` becomes Today's order only.
  The review card's rows include the two estimates.
- **Extraction endpoint:** `POST /sessions/{id}/screens/{screen_id}/extract` with `{text, request_key}`. Keyed like
  the other model calls (a retry never calls twice), logged in `llm_call`, shown in "What the model saw".
- **`claude_client.build_extract_request(MemberText, QuestionRefs, CatalogRef)`:** structured output with one field
  per covered question; each is an enum of that question's option ids (arrays for multi-choice), a catalog id for
  the health concern, the member's own words for medications and "anything else", or `null` for "not mentioned",
  plus a confidence. `QuestionRefs` holds question text and option ids/labels from our schema, nothing else.
- **Server re-checks** every value with `answers.validate`; anything invalid is dropped to "not mentioned".
- **Saving:** the voice screen submits `{"rows": {...}}` like the review card; each covered answer is its own row
  with source `voice_confirmed` (unchanged) or `member` (edited or tapped). Covered screens then don't appear. The
  `source` column is plain text, so no migration.
- **Config:** voice text up to 1,500 characters (condition text stays at 300); per-session model cap 5 → 8
  (3 extractions, a condition retry, the summary, headroom).
- **Offline stand-in:** `offline_model.py` learns extraction (keyword match per question) for end-to-end runs.

## The baseline

The finish screen shows what Today's order would have required, computed in code from the question schema, not
from a second run: every screen Today's order shows, and the **minimum** taps for each (pick and Continue for a
choice, Continue for an info screen, and so on). It is labelled "at least", so it can only understate the
saving. Today's order, and members B and C, stay in the backend and its tests; they are just not offered in the UI.

## Privacy

- The model sees only what the member said or typed (identifiers stripped) and our own question and condition
  lists. No Health-linked question is in the extraction schema, so a weight said aloud is never extracted.
- `test_claude_client` allows the new `QuestionRefs` type and still forbids every Health type and import.
- The canary test adds an extraction call for every member.

## Tests and eval

- Unit: schema checks, extraction parsing and re-validation, provenance, idempotent submit, caps, the baseline count.
- End to end: the single scenario on desktop and phone sizes, typing path, axe scan.
- **Extraction eval:** about 30 synthetic transcripts with expected answers per question, including "not
  mentioned", conflicting statements and a prompt injection. Dry run is free; the live run is about 30 calls and
  needs an OK first.

## Steps (one commit each, `make check` passing)

1. Schema: `voice` kind, estimates on the review card, `dietitian_note` moved.
2. Backend extraction: `claude_client`, endpoint, offline stand-in, canary and firewall tests.
3. Saving voice answers, provenance, stats, the baseline count.
4. Web: single-scenario start, review card estimate rows, `VoiceScreen` (speech plus typing).
5. Finish screen and dietitian view.
6. End-to-end tests; README and the older plan updated.
7. Extraction eval (live run with OK).

# Eatopia demo: plan (v2, after reading their site)

Status: the first concept ("Sprout": HealthKit ingest → a nightly agent writes a next step → dietitian review) is
**dropped**. Most of it already ships, and its core would break Eatopia's own privacy rule. Pick a direction below.

Sources read on 2026-11-12:

- eatopia.ai: home, FAQ, /conditions, /privacy (last updated 27 Sep 2026), /support
- The App Store listing
- Cecilia's hiring post
- Hongkun Gong's LinkedIn profile

## What Eatopia already has

| Area | What exists (source) |
|---|---|
| AI guide | **Sage**: Claude, curated clinical knowledge base, PubMed links (privacy, Hongkun's profile) |
| Meal logging | One-photo meal reads that give "the one thing to change next time"; foods mapped to USDA data (App Store, profile) |
| Plans | Condition-aware plan checked against allergies, avoided foods and **medicines**; a dietitian reviews it (App Store) |
| Targets | Deterministic engine for energy and nutrient targets with **no model calls** (privacy) |
| Safety | Every message screened by rules; some go to a person; on-call dietitian alerts via Twilio; append-only audit trail (privacy) |
| Apple Health | Steps, workouts, height, weight, resting heart rate, sleep; cycle and glucose as separate consents (privacy) |
| Devices | **Oura, Withings, Whoop, Dexcom**, connected directly with OAuth (privacy) |
| Labs | Lab-report upload → summary + extracted values; original file not kept (privacy) |
| Proactive | Meal and wind-down reminders timed to sleep; optional **SMS coaching** check-ins (privacy) |
| Places | "Places to eat nearby when you ask" (App Store) |
| Platform | iPhone app, web app (app.eatopia.ai), FastAPI/Postgres on Railway, Stripe + IAP, Resend, Sentry |

## Hard constraints from their privacy policy (any demo must respect these)

1. **Device data never goes to the language model.** Nothing from Apple Health, Oura, Withings, Whoop, Dexcom or a
   glucose monitor is sent to Anthropic. The policy says: *"This is a rule in our code with a test that fails if anyone
   changes it."* Only the deterministic parts of the product use device data.
2. **Glucose is for the dietitian.** Readings are not shown back to the member and do not change the plan
   automatically.
3. **The model does no clinical math.** Targets and plans come from a deterministic engine.
4. Identifiers are removed by pattern matching before anything is sent to the model.
5. Cycle phases are shown as *estimated*, never for PCOS, hormonal contraception, or irregular cycles.

Sprout v1 fed HealthKit and CGM signals into an agent. That breaks rule 1, and Hongkun would see it immediately.

## Gaps backed by evidence

| Gap | Evidence |
|---|---|
| **MCP** | Named in the job post; nothing on the site or the App Store listing. *Outdated (2026-11-13): Sage already uses 6 read-only tools over member data, so tool use is not a gap.* |
| **Citation checking at display time** | Privacy policy: *"We do not independently verify every citation at the moment it is shown"* |
| **Making device data useful to the dietitian** | Glucose is kept "for your dietitian to review" so "your clinician put[s] that in context". Nothing describes analysis that does this for them; the job post asks to "turn health data into practical, personalized guidance" |
| **Garmin, Fitbit, Google Fit** | "We do not connect to Garmin, Fitbit or Google Fit today… so we can plan for future support" |
| **"What to buy"** | Cecilia's Dinner Lab post: "what to buy, what to eat"; no grocery feature on the site or App Store listing |
| **CES 2027 booth** | Booth #60849; nothing public about a booth demo |

## Candidate directions

### A. Meal Response Lab + a policy-safe MCP server (recommended)

- **Meal-response engine:** deterministic, no LLM.
  - Joins CGM readings with logged meals and computes, per meal: baseline, peak change, time to peak, area under the
    curve above baseline over 2 hours, and how long it takes to return to baseline.
  - Finds repeat patterns ("white-rice dinners: median +78 mg/dL; same dinner after a 15-minute walk: +41").
  - Takes into account sleep the night before and an estimated cycle phase.
- **Dietitian console view:** the evidence the dietitian needs to "put it in context". Nothing is shown to the member
  and the plan never changes automatically, which matches rule 2.
- **MCP server with a data-classification firewall:**
  - Every field is tagged `device`, `member_reported`, or `reference`.
  - Model-facing tools can't return `device` fields, enforced by types and a test that fails if anyone changes it,
    mirroring their own rule.
  - Tools: plan, targets, meal log, food lookup, and an aggregate meal-response summary that only the dietitian can
    request.
- **Stretch:** a citation-verifier tool.
- **Covers all three job-post skills:** backend and databases; agents, tool calling and MCP; health data.

### B. Citation verifier service

Every PMID Sage cites is checked when it's shown:

1. Does the PMID exist (NCBI E-utilities)?
2. Do the title, year and authors match what was cited?
3. Does the abstract actually support the claim? An LLM judge checks this; abstracts aren't member data, so the
   privacy rules allow it.

Includes a cache, an eval set and a precision/recall report. It fixes a gap they admit to, and Cecilia (a PhD
scientist) will care. It's narrower and more AI-heavy, with little health-data work.

### C. Garmin / Fitbit connector

OAuth plus incremental sync into the same tables as their existing device connectors, with deletion when a member
disconnects. It's on their roadmap, but it's narrow: Garmin's API needs partner approval, and it only shows plumbing.

### D. Grocery list ("what to buy")

Turns a plan into a condition-safe grocery list with swaps, then sends it to an Instacart shopping-list link. It's
product-visible and fun at a booth, but less of an AI and backend showcase.

Details for the chosen direction (architecture, milestones, evals) get written after the pick. Stack stays
Python / FastAPI / Postgres, with synthetic data only and no Eatopia branding on the public demo.

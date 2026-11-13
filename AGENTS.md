# AGENTS.md: Health-first onboarding demo

A mobile-first web app that shows an easier onboarding: answers Apple Health can give are suggested and the
member confirms them. Built in Eatopia's stack: Next.js (App Router) in `web/`, FastAPI in `backend/`, Postgres,
deployed on Railway. The plan is [docs/plan-health-prefill.md](docs/plan-health-prefill.md); read it first.
`PLAN.md` holds the earlier research and Eatopia's privacy rules.

## Commands

- `make check`: everything CI runs (backend ruff, mypy, pytest; web lint and typecheck; the Railway file's
  types). Run it before every commit.
- `make backend-dev`: API on http://localhost:8000. `make migrate` applies database migrations.
- Backend tests need Postgres: a local `intake_test` database (`createdb intake_test`), or `TEST_DATABASE_URL`.
  The dev server uses `intake` (`DATABASE_URL`).
- Model calls need `ANTHROPIC_API_KEY` (or an `ant auth login` profile). Tests never need it: unit tests use
  `tests/fakes.py`, and end-to-end runs set `LLM_TRANSPORT=offline` (a keyword matcher, `app/offline_model.py`).
- `cd backend && uv run python -m evals.condition_match` is a free dry run of the condition-match eval;
  `--live` makes one real Claude call per case (about 50). Ask before running it.
- `make web-dev`: web app on http://localhost:3000 (Next picks 3001 if 3000 is busy; then start the API with
  `ALLOWED_ORIGINS='["http://localhost:3001"]'`).
- `make e2e`: Playwright runs on desktop and phone sizes. It starts its own API (port 8100, database
  `intake_e2e`) and a production build of the web app (port 3100). First time: `createdb intake_e2e` and
  `cd web && npx playwright install chromium`.

## Rules for this repo

- **No Health value ever reaches the model.** Only `backend/app/claude_client.py` calls Claude, and it accepts
  member-entered text and catalog references only. The canary test must stay green. Don't weaken it.
- **Synthetic data only**, labelled as synthetic on screen. No personal data anywhere in the repo.
- **The repo and the demo are public.** No Eatopia branding, colours, copy or screenshots of their app.
- Health-to-answer mapping is plain code with thresholds in config, never a model call.
- Tests never call the network or a paid API; use recorded fixtures and the fake Claude client. Ask before running
  more than about 10 real API calls.
- `web/` uses a newer Next.js than you may know: read `web/AGENTS.md` and the guide in
  `web/node_modules/next/dist/docs/` before writing web code.

## Deploying

- Railway project `eatopia-demo`, described in `.railway/railway.ts`; see `docs/plan-m8-deploy.md`.
- `railway config plan` is safe. **Ask before** `railway config apply`, `railway domain`, `railway up` or any
  other command that creates, changes or deploys anything.
- `ANTHROPIC_API_KEY` is set by hand in the Railway dashboard, never in the repo or a command line.

## Git

- One branch per milestone (`feat/m2-rules`, ...), merged to `main` by pull request once CI passes; one commit per
  step, with `make check` passing.
- **Ask before pushing.** Pushing publishes to a public repo.

# AGENTS.md: Health-first onboarding demo

A web app, shaped like a phone, that shows an easier onboarding: answers Apple Health can give are suggested and the
member confirms them. Built in Eatopia's stack: Next.js (App Router) in `web/`, FastAPI in `backend/`, Postgres,
deployed on Railway. The plan is [docs/plan-health-prefill.md](docs/plan-health-prefill.md); read it first.
`PLAN.md` holds the earlier research and Eatopia's privacy rules.

## Commands

- `make check`: everything CI runs (backend ruff, mypy, pytest; web lint and typecheck). Run it before every commit.
- `make backend-dev`: API on http://localhost:8000.
- `make web-dev`: web app on http://localhost:3000.

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

## Git

- Work on `feat/health-prefill`; one commit per milestone step, with `make check` passing.
- **Ask before pushing.** Pushing publishes to a public repo.

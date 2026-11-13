# M8 plan: deploy to Railway (code prep done; nothing created yet)

Everything below stays on paper until you approve each gate. Railway CLI 5.71 is signed in as you, in the
workspace "Devashish Juyal's Projects" (existing projects: `backend`, `sama4`). That workspace has **no spending
limit set**.

## What goes live

One new Railway project, `eatopia-demo`, with three services:

| Service | What it runs | Public? |
|---|---|---|
| `web` | Next.js production build (`web/`) | Yes: the demo link, `*.up.railway.app` |
| `api` | FastAPI (`backend/`), database migrations run before each deploy | Yes: the browser calls it directly; CORS allows only the web URL |
| `postgres` | Railway Postgres | No: private network only |

All data is synthetic. Sessions are deleted after 24 hours. Nothing personal is stored or logged.

## Step 1: code prep (a PR, no deploy)

1. **Dockerfiles** for `api` (Python 3.13 with uv, non-root, `uvicorn` on `$PORT`) and `web` (Node 22, `next build`,
   `next start` on `$PORT`). Explicit builds that run the same everywhere.
2. **`.railway/railway.ts`**, Railway's current infrastructure-as-code file (the older `railway.json` format is
   deprecated), describing the three services: root folders, Dockerfiles, `/health` checks, the pre-deploy
   migration, and variables that reference each other (the API reads Postgres's URL, the web build reads the API's
   URL). `railway config plan` shows exactly what would change before anything is applied.
3. **Production settings in the API:**
   - Accept Railway's `postgresql://` URL (we use the psycopg driver).
   - Refuse to start in production with the offline stand-in turned on.
   - A per-address limit on starting sessions (about 20 an hour) on top of the existing model caps: 5 calls a
     session and 300 a day.
4. ~~Sentry~~: not used (decided 2026-11-13). Errors are read from Railway's logs (`railway logs`).

## Step 2: gates that need your go-ahead

| Gate | What happens | Who |
|---|---|---|
| A. Create | `railway init --name eatopia-demo` (an empty project), link this repo to it, show `railway config plan`, then `railway config apply` (three services and Postgres) and `railway domain` for `web` and `api` (Railway's generated addresses can't be described in the file). | Me, after your OK |
| B. API key | You paste `ANTHROPIC_API_KEY` into the `api` service's variables in the Railway dashboard. I never see it. | You |
| C. First deploy | Deploy both services, then check: `/health`, a full run of both orders on a laptop and a phone, one real condition match and one summary (2 to 3 Sonnet calls). | Me, after your OK |
| ~~D. Limits~~ | Not set (decided 2026-11-13). Spend is bounded by the app's own caps: 5 model calls a session, 300 a day, 20 new sessions an hour per address. | – |

## Cost

- **Railway:** usage-based. Three small always-on services; I'll read the real figure with `railway usage` after a
  day rather than guess.
- **Anthropic (Sonnet 5.5):** one call is about 1,000 input and up to 500 output tokens, roughly $0.007. The daily
  cap of 300 calls bounds the worst case at about $2 a day; normal use is far below that.

## Risks

- **A public API gets poked at.** It has the session limit and the model caps (no platform spending limit, by decision), no secrets in
  responses, and only synthetic data.
- **The web app bakes the API's URL in at build time** (Next.js `NEXT_PUBLIC_` variables), so changing the API's
  domain means rebuilding `web`. The infrastructure file wires this up.
- **Rollback:** redeploy the previous build from the dashboard, or `railway down`. After the job search, delete
  the project.

## Step 1 status (code prep)

Done on `feat/m8-deploy`; nothing created or deployed.

- `backend/Dockerfile`, `web/Dockerfile` (Next.js standalone server) and their `.dockerignore` files.
- `.railway/railway.ts`: Postgres, `api` (Dockerfile build, `alembic upgrade head` before each deploy, `/health`
  check) and `web`, deploying from `main`. The services reference each other's Railway addresses, and
  `ANTHROPIC_API_KEY` is marked `preserve()` so applying the file never clears the key you set by hand.
  `make check` typechecks the file against Railway's SDK.
- API: Railway's database URL is accepted, the offline stand-in is refused in production, and one client
  address can start 20 sessions an hour (the right-most X-Forwarded-For entry, which can't be forged).
- Checked without Docker, which isn't running on this machine: the API in production mode with a
  `postgresql://` URL (migrations, `/health`, session start), the standalone web server with the API address
  baked in, and all 43 end-to-end runs against that same standalone server. The Docker images themselves are
  first built by Railway at gate C.
- Sentry: not used, by decision.

# M8 plan: deploy to Railway (draft, nothing created yet)

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
4. **Sentry** for errors in both services, as in their stack, if you have a Sentry project (see the questions).

## Step 2: gates that need your go-ahead

| Gate | What happens | Who |
|---|---|---|
| A. Create | Show `railway config plan`, then `railway config apply`: creates the project, three services and Postgres. Nothing serves traffic yet. | Me, after your OK |
| B. API key | You paste `ANTHROPIC_API_KEY` into the `api` service's variables in the Railway dashboard. I never see it. | You |
| C. First deploy | Deploy both services, then check: `/health`, a full run of both orders on a laptop and a phone, one real condition match and one summary (2 to 3 Sonnet calls). | Me, after your OK |
| D. Limits (recommended) | A hard spending limit on the Railway workspace (for example $10 a month), and a spend limit on the Anthropic workspace that holds the key. | You, or me with your OK for Railway |

## Cost

- **Railway:** usage-based. Three small always-on services; I'll read the real figure with `railway usage` after a
  day rather than guess.
- **Anthropic (Sonnet 5.5):** one call is about 1,000 input and up to 500 output tokens, roughly $0.007. The daily
  cap of 300 calls bounds the worst case at about $2 a day; normal use is far below that.

## Risks

- **A public API gets poked at.** It has the session limit, the model caps, the spending limits, no secrets in
  responses, and only synthetic data.
- **The web app bakes the API's URL in at build time** (Next.js `NEXT_PUBLIC_` variables), so changing the API's
  domain means rebuilding `web`. The infrastructure file wires this up.
- **Rollback:** redeploy the previous build from the dashboard, or `railway down`. After the job search, delete
  the project.

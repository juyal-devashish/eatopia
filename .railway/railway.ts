import { defineRailway, github, postgres, preserve, service } from "railway/iac";

// The demo's Railway project: the API and its database. The web app is hosted on Vercel (Railway's free plan has no
// room for a third service). `railway config plan` previews changes; nothing changes until `railway config apply`.
// Generated *.up.railway.app domains can't be described here; the API gets one with `railway domain`.
const REPO = "juyal-devashish/eatopia";

export default defineRailway((_ctx, project) => {
  const db = postgres("postgres");

  const api = service("api", {
    source: github(REPO, { rootDirectory: "backend", branch: "main" }),
    build: { builder: "DOCKERFILE", watchPatterns: ["/backend/**"] },
    preDeploy: "alembic upgrade head",
    healthcheck: "/health",
    env: {
      ENVIRONMENT: "production",
      DATABASE_URL: db.env.DATABASE_URL,
      // The Vercel production address of the web app (web/ on Vercel, project eatopia-demo).
      ALLOWED_ORIGINS: '["https://eatopia-demo.vercel.app"]',
      // Added by hand in the Railway dashboard. Never in the repo; `preserve()` keeps whatever is set there.
      ANTHROPIC_API_KEY: preserve(),
    },
  });

  return project("eatopia-demo", { resources: [db, api] });
});

import { defineRailway, github, postgres, preserve, service } from "railway/iac";

// The demo's Railway project. `railway config plan` previews changes; nothing changes until `railway config apply`.
// Generated *.up.railway.app domains can't be described here; each public service gets one with `railway domain`.
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
      ALLOWED_ORIGINS: '["https://${{web.RAILWAY_PUBLIC_DOMAIN}}"]',
      // Added by hand in the Railway dashboard. Never in the repo; `preserve()` keeps whatever is set there.
      ANTHROPIC_API_KEY: preserve(),
    },
  });

  const web = service("web", {
    source: github(REPO, { rootDirectory: "web", branch: "main" }),
    build: { builder: "DOCKERFILE", watchPatterns: ["/web/**"] },
    healthcheck: "/",
    env: {
      // Read at build time (web/Dockerfile): the browser bundle calls the API at this address.
      NEXT_PUBLIC_API_URL: "https://${{api.RAILWAY_PUBLIC_DOMAIN}}",
    },
  });

  return project("eatopia-demo", { resources: [db, api, web] });
});

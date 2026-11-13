import { defineConfig, devices } from "@playwright/test";

// End-to-end runs use their own ports and database, so they never touch a dev server or dev data.
const API_PORT = 8100;
const WEB_PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://localhost:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 960 } } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: `uv run alembic upgrade head && uv run uvicorn app.main:app --port ${API_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${API_PORT}/health`,
      env: {
        ...process.env,
        DATABASE_URL: process.env.E2E_DATABASE_URL ?? "postgresql+psycopg:///intake_e2e",
        ALLOWED_ORIGINS: `["http://localhost:${WEB_PORT}"]`,
        // Never call a paid API from tests: a keyword matcher answers in Claude's place.
        LLM_TRANSPORT: "offline",
        // Every test starts sessions from the same address; the per-client limit is covered by backend tests.
        SESSIONS_PER_HOUR_PER_CLIENT: "0",
      },
      timeout: 120_000,
    },
    {
      // The same standalone server the production image runs (web/Dockerfile).
      command:
        "npm run build && mkdir -p public && cp -r public .next/standalone/ && " +
        "cp -r .next/static .next/standalone/.next/ && node .next/standalone/server.js",
      url: `http://localhost:${WEB_PORT}`,
      env: {
        ...process.env,
        NEXT_PUBLIC_API_URL: `http://localhost:${API_PORT}`,
        NEXT_OUTPUT: "standalone",
        PORT: String(WEB_PORT),
        HOSTNAME: "localhost",
      },
      timeout: 300_000,
    },
  ],
});

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
      },
      timeout: 120_000,
    },
    {
      command: `npm run build && npx next start -p ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      env: { ...process.env, NEXT_PUBLIC_API_URL: `http://localhost:${API_PORT}` },
      timeout: 300_000,
    },
  ],
});

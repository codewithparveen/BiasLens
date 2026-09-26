import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke-test config. Requires the backend (uvicorn, port 8000) and the
 * frontend dev server (vite, port 5173) to already be running -- this does
 * NOT boot them for you, since the demo backend needs its own Python env.
 *
 * Run:
 *   npx playwright install chromium   (first time only)
 *   npx playwright test
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

import { defineConfig, devices } from "@playwright/test";

const apiURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const webURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./tests",
  timeout: 45_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["line"]] : "list",
  use: {
    baseURL: webURL,
    trace: "on-first-retry",
    acceptDownloads: true
  },
  webServer: [
    {
      command: "python3 tests/fixtures/jira.py",
      url: "http://127.0.0.1:8766/health",
      timeout: 30_000,
      reuseExistingServer: false
    },
    {
      command: "AEGISDESK_TICKET_ADAPTER=jira AEGISDESK_JIRA_BASE_URL=http://127.0.0.1:8766 AEGISDESK_JIRA_EMAIL=e2e@example.test AEGISDESK_JIRA_API_TOKEN=controlled-test-credential AEGISDESK_JIRA_PROJECT_KEY=OPS ../../scripts/start-api-for-e2e.sh",
      url: `${apiURL}/health`,
      timeout: 120_000,
      reuseExistingServer: false
    },
    {
      command:
        "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 NEXT_PUBLIC_AEGISDESK_MODE=evaluation NEXT_PUBLIC_SHOW_EVALUATION_TOOLS=true npm run dev -- --hostname 127.0.0.1 --port 3000",
      url: webURL,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});

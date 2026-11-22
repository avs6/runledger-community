import { defineConfig, devices } from '@playwright/test'

// Smoke tests against a running stack (review Wave 0.5). Locally: docker compose up, then
// `npm run e2e`. Point E2E_BASE_URL elsewhere to test another environment you own.
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3201',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})

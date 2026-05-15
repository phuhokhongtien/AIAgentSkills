import { defineConfig, devices } from '@playwright/test';

// Offline, self-contained: tests use page.setContent (no web server, no network).
export default defineConfig({
  testDir: './tests',
  reporter: 'list',
  retries: 0,
  use: {
    ...devices['Desktop Chrome'],
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  fullyParallel: true,
  reporter: [['list'], ['html', { open: 'never' }]],
  retries: 0,
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL ?? 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  projects: [
    {
      name: 'chromium-e2e',
    },
  ],
});

import { expect, test } from '@playwright/test';

test('renders the Events app shell in Chromium', async ({ page }) => {
  test.setTimeout(90_000);

  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({
      body: JSON.stringify({
        code: 0,
        data: {
          actor_id: 'local_dev',
          actor_type: 'development',
          capabilities: ['runtime.inspect'],
          csrf_token: 'csrf-smoke',
        },
        msg: 'ok',
      }),
      contentType: 'application/json',
      status: 200,
    });
  });

  await page.goto('/events');

  await expect(page.locator('.page-kicker')).toHaveText(/事件中心/, {
    timeout: 60_000,
  });
  await expect(page.locator('.page-title')).toHaveText(/事件/, {
    timeout: 60_000,
  });
});

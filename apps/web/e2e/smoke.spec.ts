import { expect, test } from '@playwright/test';

test('renders the Events app shell in Chromium', async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto('/events');

  await expect(page.locator('.page-kicker')).toHaveText(/event inbox/i, {
    timeout: 60_000,
  });
  await expect(page.locator('.page-title')).toHaveText(/events/i, {
    timeout: 60_000,
  });
});

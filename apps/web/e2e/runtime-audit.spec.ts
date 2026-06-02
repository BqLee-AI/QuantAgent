import { expect, test } from '@playwright/test';

test('renders runtime audit chat view through the real API session', async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto('/runtime');

  await expect(page.locator('.page-title')).toHaveText('Runtime 审计', {
    timeout: 60_000,
  });
  await expect(page.getByText('受控 fixture 样例')).toBeVisible();
  await expect(page.getByText('以 Router Agent 为首个样例')).toBeVisible();
  await expect(page.getByRole('heading', { name: /SK Hynix raises HBM capacity/ })).toBeVisible();
  await expect(page.getByText('发布 event.routed')).toBeVisible();

  await page.getByPlaceholder('time_to').fill('2026-06-03T01:00:00.000Z');
  await page.getByPlaceholder('trace_id').fill('trace_review');

  await expect(page.getByRole('heading', { name: /Hyperscaler capex outlook/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /SK Hynix raises HBM capacity/ })).toHaveCount(0);
});

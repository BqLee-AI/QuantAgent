import { expect, test, type Page } from '@playwright/test';

type AuthActor = {
  actor_id: string;
  actor_type: string;
  capabilities: string[];
  csrf_token: string;
};

const actor: AuthActor = {
  actor_id: 'local_admin',
  actor_type: 'local_single_user',
  capabilities: ['runtime.inspect', 'plugin.configure'],
  csrf_token: 'csrf-e2e',
};

const developmentActor: AuthActor = {
  ...actor,
  actor_id: 'local_dev',
  capabilities: ['runtime.inspect', 'plugin.configure'],
};

function envelope<T>(data: T, msg = 'ok') {
  return {
    code: 0,
    data,
    msg,
  };
}

function unauthorized() {
  return {
    code: 401,
    data: null,
    error: {
      code: 'UNAUTHORIZED',
      request_id: 'req-e2e-unauthorized',
    },
    msg: 'unauthorized',
  };
}

async function mockAuth(
  page: Page,
  options: { actor?: AuthActor; authenticated?: boolean } = {},
) {
  let authenticated = options.authenticated ?? false;
  const responseActor = options.actor ?? actor;
  let logoutCsrf: string | null = null;

  await page.route('**/api/v1/me', async (route) => {
    if (!authenticated) {
      await route.fulfill({
        body: JSON.stringify(unauthorized()),
        contentType: 'application/json',
        status: 401,
      });
      return;
    }

    await route.fulfill({
      body: JSON.stringify(envelope(responseActor)),
      contentType: 'application/json',
      status: 200,
    });
  });

  await page.route('**/api/v1/auth/login', async (route) => {
    const payload = route.request().postDataJSON() as { password?: string };

    if (payload.password !== 'correct-password') {
      await route.fulfill({
        body: JSON.stringify(unauthorized()),
        contentType: 'application/json',
        status: 401,
      });
      return;
    }

    authenticated = true;
    await route.fulfill({
      body: JSON.stringify(envelope(responseActor)),
      contentType: 'application/json',
      status: 200,
    });
  });

  await page.route('**/api/v1/auth/logout', async (route) => {
    logoutCsrf = route.request().headers()['x-csrf-token'] ?? null;
    authenticated = false;
    await route.fulfill({
      body: JSON.stringify(envelope({ cleared: true })),
      contentType: 'application/json',
      status: 200,
    });
  });

  return {
    getLogoutCsrf: () => logoutCsrf,
  };
}

test('redirects protected routes to login and restores the original target', async ({ page }) => {
  await mockAuth(page);

  await page.goto('/events');

  await expect(page).toHaveURL(/\/login\?redirect=%2Fevents/);
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();

  await page.getByLabel('Administrator password').fill('correct-password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page).toHaveURL(/\/events/);
  await expect(page.locator('.page-title')).toHaveText('Events');
});

test('shows login failure without leaking submitted password', async ({ page }) => {
  await mockAuth(page);

  await page.goto('/login');
  await page.getByLabel('Administrator password').fill('wrong-password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page.getByRole('alert')).toHaveText('Password is invalid.');
  await expect(page.getByText('wrong-password')).toHaveCount(0);
});

test('restores an existing session through /me and logs out with CSRF', async ({ page }) => {
  const auth = await mockAuth(page, { authenticated: true });

  await page.goto('/events');

  await expect(page.locator('.page-title')).toHaveText('Events');
  await expect(page.getByText('local_admin')).toBeVisible();

  await page.getByRole('button', { name: 'Logout' }).click();

  await expect(page).toHaveURL(/\/login/);
  expect(auth.getLogoutCsrf()).toBe('csrf-e2e');
});

test('auth-disabled development actor enters the dashboard with a visible marker', async ({ page }) => {
  await mockAuth(page, {
    actor: developmentActor,
    authenticated: true,
  });

  await page.goto('/events');

  await expect(page.getByText('Development auth disabled')).toBeVisible();
  await expect(page.locator('.page-title')).toHaveText('Events');
});

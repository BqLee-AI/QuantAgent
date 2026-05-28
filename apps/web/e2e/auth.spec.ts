import { expect, test, type Page } from '@playwright/test';

type AuthActor = {
  actor_id: string;
  actor_type: string;
  capabilities: string[];
  csrf_token: string;
};

type RefreshedSession = AuthActor & {
  expires_at: number;
  max_expires_at: number;
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

function forbiddenEnvelope() {
  return {
    code: 403,
    data: null,
    msg: '当前账号没有执行该操作的权限。',
    request_id: 'req-e2e-forbidden',
    trace_id: 'trace-e2e-forbidden',
  };
}

function refreshedSession(actor: AuthActor): RefreshedSession {
  const nowSeconds = Math.floor(Date.now() / 1000);

  return {
    ...actor,
    expires_at: nowSeconds + 3600,
    max_expires_at: nowSeconds + 7200,
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

  await page.route('**/api/v1/auth/refresh', async (route) => {
    if (!authenticated) {
      await route.fulfill({
        body: JSON.stringify(unauthorized()),
        contentType: 'application/json',
        status: 401,
      });
      return;
    }

    await route.fulfill({
      body: JSON.stringify(envelope(refreshedSession(responseActor))),
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
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();

  await page.getByLabel('管理员密码').fill('correct-password');
  await page.getByRole('button', { name: '登录' }).click();

  await expect(page).toHaveURL(/\/events/);
  await expect(page.locator('.page-title')).toHaveText('高价值事件');
});

test('shows login failure without leaking submitted password', async ({ page }) => {
  await mockAuth(page);

  await page.goto('/login');
  await page.getByLabel('管理员密码').fill('wrong-password');
  await page.getByRole('button', { name: '登录' }).click();

  await expect(page.getByRole('alert')).toHaveText('密码不正确。');
  await expect(page.getByText('wrong-password')).toHaveCount(0);
});

test('restores an existing session through /me and logs out with CSRF', async ({ page }) => {
  const auth = await mockAuth(page, { authenticated: true });

  await page.goto('/events');

  await expect(page.locator('.page-title')).toHaveText('高价值事件');
  await expect(page.getByText('local_admin')).toBeVisible();

  await page.getByRole('button', { name: '退出登录' }).click();

  await expect(page).toHaveURL(/\/login/);
  expect(auth.getLogoutCsrf()).toBe('csrf-e2e');
});

test('authenticated development actor enters the dashboard without auth-disabled marker when auth is enabled', async ({ page }) => {
  await mockAuth(page, {
    actor: developmentActor,
    authenticated: true,
  });

  await page.goto('/events');

  await expect(page.getByText('开发环境已关闭鉴权')).toHaveCount(0);
  await expect(page.getByText('local_dev')).toBeVisible();
  await expect(page.locator('.page-title')).toHaveText('高价值事件');
});

test('authenticated users without route capability stay in forbidden flow instead of returning to login', async ({
  page,
}) => {
  await mockAuth(page, {
    actor: {
      ...actor,
      capabilities: ['runtime.inspect'],
    },
    authenticated: true,
  });

  await page.goto('/plugins');

  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.getByRole('heading', { name: '当前页面不可访问' })).toBeVisible();
  await expect(page.getByText('当前账号没有执行该操作的权限。')).toBeVisible();
  await expect(page.getByRole('link', { name: '插件' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '返回可访问入口' })).toBeVisible();
});

test('root route waits for session capabilities before choosing the default entry', async ({ page }) => {
  await mockAuth(page, {
    actor: {
      ...actor,
      capabilities: ['secret.manage'],
    },
    authenticated: true,
  });

  await page.goto('/');

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: '半导体新闻流' })).toBeVisible();
  await expect(page.getByRole('link', { name: '模型' })).toBeVisible();
});

test('forbidden API responses preserve diagnostics without leaking sensitive values', async ({ page }) => {
  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({
      body: JSON.stringify(forbiddenEnvelope()),
      contentType: 'application/json',
      status: 403,
    });
  });

  await page.goto('/plugins');

  await expect(page.getByRole('heading', { name: '当前页面不可访问' })).toBeVisible();
  await expect(page.getByText('request_id')).toBeVisible();
  await expect(page.getByText('req-e2e-forbidden')).toBeVisible();
  await expect(page.getByText('trace_id')).toBeVisible();
  await expect(page.getByText('trace-e2e-forbidden')).toBeVisible();
  await expect(page.getByText('correct-password')).toHaveCount(0);
});

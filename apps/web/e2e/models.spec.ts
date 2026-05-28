import { expect, test } from '@playwright/test';

import { mockApiSuccess } from './mocks/mockEnvelope';
import { createRouteMock } from './mocks/route-mock';

const authActor = {
  actor_id: 'model_admin',
  actor_type: 'local_single_user',
  capabilities: ['secret.manage', 'runtime.inspect'],
  csrf_token: 'csrf-models-e2e',
};

const providerList = {
  default_provider_id: 1,
  providers: [
    {
      id: 1,
      provider_type: 'openai_compatible',
      name: 'OpenAI Production',
      base_url: 'https://api.openai.com/v1',
      enabled: true,
      is_default: true,
      status: 'configured',
      key_status: 'configured',
      masked_key: 'sk-...prod',
      last_error: null,
      model_count: 2,
      updated_at: '2026-05-28T10:00:00Z',
    },
    {
      id: 2,
      provider_type: 'openai_compatible',
      name: 'Backup Gateway',
      base_url: 'https://gateway.internal/v1',
      enabled: false,
      is_default: false,
      status: 'disabled',
      key_status: 'missing',
      masked_key: null,
      last_error: null,
      model_count: 1,
      updated_at: '2026-05-28T09:00:00Z',
    },
  ],
};

const providerDetails = {
  1: {
    ...providerList.providers[0],
    models: [
      {
        id: 11,
        provider_id: 1,
        model_name: 'gpt-5.4',
        enabled: true,
        supports_vision: false,
        is_global_default: true,
        created_at: '2026-05-28T10:00:00Z',
        updated_at: '2026-05-28T10:00:00Z',
      },
      {
        id: 12,
        provider_id: 1,
        model_name: 'gpt-5.4-vision',
        enabled: true,
        supports_vision: true,
        is_global_default: false,
        created_at: '2026-05-28T10:05:00Z',
        updated_at: '2026-05-28T10:05:00Z',
      },
    ],
  },
  2: {
    ...providerList.providers[1],
    models: [
      {
        id: 21,
        provider_id: 2,
        model_name: 'gateway-mini',
        enabled: false,
        supports_vision: false,
        is_global_default: false,
        created_at: '2026-05-28T09:00:00Z',
        updated_at: '2026-05-28T09:00:00Z',
      },
    ],
  },
};

const presets = [
  {
    preset_key: 'global_default',
    title: '全局默认模型',
    description: '没有更具体任务设置时使用。',
    primary_model: providerDetails[1].models[0],
    fallback_model: providerDetails[1].models[1],
    status: 'configured',
    validation_message: null,
  },
  {
    preset_key: 'multimodal',
    title: '多模态任务',
    description: '需要视觉理解能力时使用。',
    primary_model: providerDetails[1].models[1],
    fallback_model: null,
    status: 'configured',
    validation_message: null,
  },
];

const invocations = [
  {
    id: 101,
    provider_id: 1,
    provider_type: 'openai_compatible',
    provider_name: 'OpenAI Production',
    model: 'gpt-5.4',
    preset_key: 'global_default',
    status: 'succeeded',
    token_usage: {
      prompt_tokens: 128,
      completion_tokens: 64,
      total_tokens: 192,
    },
    error_summary: null,
    request_id: 'req-models-e2e',
    trace_id: 'trace-models-e2e',
    agent_run_id: 'run-models-e2e',
    created_at: '2026-05-28T10:10:00Z',
  },
];

test('renders model provider management and captures the page state', async ({ page }) => {
  test.setTimeout(90_000);

  const routeMock = createRouteMock(page);

  await routeMock.mockApiRoute('GET', '/api/v1/me', mockApiSuccess(authActor));
  await routeMock.mockApiRoute('POST', '/api/v1/auth/refresh', mockApiSuccess(authActor));
  await routeMock.mockApiRoute('GET', '/api/v1/models/providers', mockApiSuccess(providerList));
  await routeMock.mockApiRoute(
    'GET',
    /\/api\/v1\/models\/providers\/\d+$/,
    (request) => {
      const providerId = Number(request.pathname.split('/').at(-1));
      return mockApiSuccess(providerDetails[providerId as keyof typeof providerDetails]);
    },
  );
  await routeMock.mockApiRoute('GET', '/api/v1/models/presets', mockApiSuccess(presets));
  await routeMock.mockApiRoute('GET', '/api/v1/models/invocations', mockApiSuccess(invocations));

  await page.goto('/models');

  await expect(page.locator('.page-title')).toHaveText('模型配置');
  await expect(page.getByRole('heading', { name: '供应商列表' })).toBeVisible();
  await expect(page.locator('span.truncate', { hasText: 'OpenAI Production' })).toBeVisible();
  await expect(page.locator('span.truncate', { hasText: 'Backup Gateway' })).toBeVisible();
  await expect(page.getByText('req-models-e2e')).toBeVisible();

  await page.getByRole('button', { name: '任务模型预设' }).click();
  await expect(page.getByRole('heading', { name: '任务模型预设' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '全局默认模型' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '多模态任务' })).toBeVisible();

  await page.getByRole('button', { name: '供应商配置' }).click();
  await page.getByRole('button', { name: '新增 Provider' }).click();
  await expect(page.getByRole('heading', { name: '选择 Provider 模板' })).toBeVisible();
  await expect(page.getByRole('button', { name: '创建 Provider' })).toBeEnabled();

  await page.screenshot({
    fullPage: true,
    path: test.info().outputPath('models-page.png'),
  });
});

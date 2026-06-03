import { expect, test } from '@playwright/test';

import { mockApiSuccess } from './mocks/mockEnvelope';
import { createRouteMock } from './mocks/route-mock';

test('renders runtime audit news view through the backend news endpoint', async ({ page }) => {
  const routeMock = createRouteMock(page);
  await routeMock.mockApiRoute(
    'GET',
    '/api/v1/me',
    mockApiSuccess({
      actor_id: 'local_admin',
      actor_type: 'local_single_user',
      capabilities: ['runtime.inspect'],
      csrf_token: 'csrf-runtime-audit',
    }),
  );
  await routeMock.mockApiRoute(
    'GET',
    '/api/v1/runtime/audit/news',
    (request) => {
      const search = new URLSearchParams(request.search);
      const items = runtimeAuditNewsItems.filter((item) => {
        const keyword = search.get('keyword');
        if (keyword && !item.title.toLowerCase().includes(keyword.toLowerCase())) return false;
        const traceId = search.get('trace_id');
        if (traceId && item.trace.trace_id !== traceId) return false;
        return true;
      });
      return mockApiSuccess({
        generated_at: '2026-06-03T02:30:00.000Z',
        items,
        next_cursor: null,
      });
    },
  );

  await page.goto('/runtime');

  await expect(page.locator('.page-title')).toHaveText('Runtime 审计');
  const packagingNews = page.getByRole('button', { name: /Advanced packaging capacity expands/ });
  await expect(packagingNews).toBeVisible();
  await packagingNews.click();
  await expect(packagingNews.getByText('采集 -> RawEvent 入库 -> 调度关联 -> AI intake 暂不可审计 -> 路由结果暂不可审计')).toBeVisible();
  await expect(page.getByText('先进封装产能扩张直接影响半导体后段供给。')).toHaveCount(2);
  await expect(page.getByText('advanced-packaging, memory')).toBeVisible();
  await page.getByRole('button', { name: '查看处理详情' }).first().click();
  await expect(page.getByRole('heading', { name: 'Router Agent 处理详情' })).toBeVisible();
  await expect(page.getByText('"schema_version": "event_intake_decision.v1"')).toBeVisible();
  await expect(page.getByText('"decision": "route"')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByText('发布 event.routed')).toHaveCount(0);
  await expect(page.getByText('收到 industry.analysis.requested')).toHaveCount(0);
  await expect(page.getByText('secret-token')).toHaveCount(0);

  await page.getByPlaceholder('标题 / URL / 摘要').fill('HBM');
  await page.getByPlaceholder('trace_id').fill('trace-runtime-001');

  await expect(page.getByRole('button', { name: /HBM supply tightens/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Advanced packaging capacity expands/ })).toHaveCount(0);
  await expect(page.getByText('run-runtime-001', { exact: true })).toBeVisible();
});

const runtimeAuditNewsItems = [
  {
    agent_stages: [
      routerAgentSuccessStage({
        rawEventId: 'rawevt-runtime-002',
        title: 'Advanced packaging capacity expands',
        url: 'https://news.example.com/articles/advanced-packaging',
        summary: '先进封装产能扩张直接影响半导体后段供给。',
      }),
      mainAgentUnavailableStage('rawevt-runtime-002'),
    ],
    author: 'Foundry Desk',
    canonical_url: 'https://news.example.com/articles/advanced-packaging',
    content_preview: 'Advanced packaging capacity expands across OSAT vendors.',
    current_stage: 'persisted',
    first_captured_at: '2026-06-02T07:01:00.000Z',
    focus_stage: 'ai_intake_unavailable',
    last_captured_at: '2026-06-02T07:01:02.000Z',
    published_at: '2026-06-02T07:00:00.000Z',
    raw_event_id: 'rawevt-runtime-002',
    safe_details: {
      capture_count: 1,
      duplicate_capture_count: 1,
      metadata: { feed: 'advanced-packaging', source: 'Packaging Daily' },
    },
    source_name: 'Packaging Daily',
    source_plugin_id: 'quantagent.official.source.rss',
    status: 'captured',
    timeline: [
      step('captured', '采集', 'success', '2026-06-02T07:01:00.000Z', '新闻已由 source plugin 捕获。'),
      step('persisted', 'RawEvent 入库', 'success', '2026-06-02T07:01:03.000Z', '采集事实已作为 RawEvent 保存。'),
      step('scheduler_linked', '调度关联', 'pending', '2026-06-02T07:01:00.000Z', '已有 capture ledger，但没有可关联的 scheduler run。'),
      step('ai_intake_unavailable', 'AI intake', 'unavailable', null, '暂无持久化 AI intake / route decision read model。'),
      step('route_unavailable', '路由结果', 'unavailable', null, 'event.routed 当前没有稳定落库结果。'),
    ],
    title: 'Advanced packaging capacity expands',
    trace: {
      binding_id: 'binding-runtime-002',
      correlation_id: null,
      raw_event_id: 'rawevt-runtime-002',
      request_id: 'req-capture-002',
      run_id: null,
      trace_id: null,
    },
    url_host: 'news.example.com',
  },
  {
    agent_stages: [
      routerAgentUnavailableStage('rawevt-runtime-001', 'HBM supply tightens'),
      mainAgentUnavailableStage('rawevt-runtime-001'),
    ],
    author: 'Memory Desk',
    canonical_url: 'https://semis.example.com/news/hbm',
    content_preview: 'HBM supply chain update for semiconductor audit.',
    current_stage: 'scheduler_linked',
    first_captured_at: '2026-06-01T09:00:01.000Z',
    focus_stage: 'ai_intake_unavailable',
    last_captured_at: '2026-06-01T09:00:02.000Z',
    published_at: '2026-06-01T08:30:00.000Z',
    raw_event_id: 'rawevt-runtime-001',
    safe_details: {
      scheduler: { captured_count: 1, duration_ms: 5000, status: 'succeeded', trigger_type: 'scheduled' },
    },
    source_name: 'SemiWire',
    source_plugin_id: 'quantagent.official.source.rss',
    status: 'linked',
    timeline: [
      step('captured', '采集', 'success', '2026-06-01T09:00:01.000Z', '新闻已由 source plugin 捕获。'),
      step('persisted', 'RawEvent 入库', 'success', '2026-06-01T09:00:03.000Z', '采集事实已作为 RawEvent 保存。'),
      step('scheduler_linked', '调度关联', 'success', '2026-06-01T09:00:00.000Z', '关联 scheduler run，状态为 succeeded。', [
        { kind: 'scheduler_run', id: 'run-runtime-001', label: 'SchedulerRun' },
      ]),
      step('ai_intake_unavailable', 'AI intake', 'unavailable', null, '暂无持久化 AI intake / route decision read model。'),
      step('route_unavailable', '路由结果', 'unavailable', null, 'event.routed 当前没有稳定落库结果。'),
    ],
    title: 'HBM supply tightens',
    trace: {
      binding_id: 'binding-runtime-001',
      correlation_id: 'corr-runtime-001',
      raw_event_id: 'rawevt-runtime-001',
      request_id: 'req-capture-001',
      run_id: 'run-runtime-001',
      trace_id: 'trace-runtime-001',
    },
    url_host: 'semis.example.com',
  },
];

function step(
  step_id: string,
  label: string,
  status: string,
  occurred_at: string | null,
  summary: string,
  refs: Array<{ id: string; kind: string; label: string }> = [],
) {
  return {
    label,
    occurred_at,
    refs,
    status,
    step_id,
    summary,
  };
}

function routerAgentSuccessStage({
  rawEventId,
  title,
  url,
  summary,
}: {
  rawEventId: string;
  title: string;
  url: string;
  summary: string;
}) {
  const output_json = {
    schema_version: 'event_intake_decision.v1',
    decision: 'route',
    discard_reason: 'not_discarded',
    quality: {
      is_spam: false,
      noise_flags: [],
      content_completeness: 'full',
      enrichment_status: 'succeeded',
      confidence: 0.88,
    },
    industry_relevance: [
      {
        industry_id: 'semiconductor',
        relationship: 'direct',
        relevance_score: 0.91,
        reason_summary: summary,
      },
    ],
    structured_news: {
      canonical_title: title,
      short_summary: summary,
      bullet_summary: ['OSAT 和先进封装产能扩张。'],
      event_type: 'capacity_expansion',
      entities: ['OSAT'],
      companies: [],
      tickers: [],
      technologies: ['advanced packaging'],
      products: ['AI accelerator package'],
      locations: [],
      numbers: [],
      time_horizon: 'near_term',
      source_facts: ['Advanced packaging capacity expands across OSAT vendors.'],
      uncertainties: [],
    },
    routing: {
      target_industries: ['semiconductor'],
      target_topics: ['advanced-packaging', 'memory'],
      priority: 'high',
      requires_deep_analysis: true,
      requires_human_review: false,
      dedupe_key_hint: url,
    },
    audit: {
      reason_summary: 'Direct semiconductor packaging relevance.',
      evidence_field_refs: ['article.title'],
      schema_validation_status: 'valid',
    },
  };

  return {
    agent_name: 'Router Agent',
    agent_type: 'router_agent',
    key_fields: {
      decision: 'route',
      short_summary: summary,
      relevance: 'semiconductor / direct / 0.91',
      target_topics: ['advanced-packaging', 'memory'],
      priority: 'high',
      requires_deep_analysis: true,
      confidence: 0.88,
      is_spam: false,
    },
    output_json,
    refs: [{ kind: 'raw_event', id: rawEventId, label: 'RawEvent' }],
    stage_id: 'router_agent',
    status: 'success',
    summary,
    unavailable_reason: null,
  };
}

function routerAgentUnavailableStage(rawEventId: string, title: string) {
  return {
    agent_name: 'Router Agent',
    agent_type: 'router_agent',
    key_fields: {
      raw_event_id: rawEventId,
      title,
      output_persistence: 'unavailable',
      expected_schema: 'event_intake_decision.v1',
    },
    output_json: null,
    refs: [{ kind: 'raw_event', id: rawEventId, label: 'RawEvent' }],
    stage_id: 'router_agent',
    status: 'unavailable',
    summary: '暂无持久化 Router Agent 结构化输出。',
    unavailable_reason: '当前数据库尚未提供 Router Agent output_json / route decision read model。',
  };
}

function mainAgentUnavailableStage(rawEventId: string) {
  return {
    agent_name: '行业 MainAgent',
    agent_type: 'industry_main_agent',
    key_fields: {
      raw_event_id: rawEventId,
      planned_view: 'chat_markdown_toolcall_stream',
    },
    output_json: null,
    refs: [{ kind: 'raw_event', id: rawEventId, label: 'RawEvent' }],
    stage_id: 'industry_main_agent',
    status: 'unavailable',
    summary: '暂无持久化行业分析输出；后续会以 Chat/Markdown/ToolCall 流形式接入。',
    unavailable_reason: 'V1 尚未落库行业 MainAgent 消费记录。',
  };
}

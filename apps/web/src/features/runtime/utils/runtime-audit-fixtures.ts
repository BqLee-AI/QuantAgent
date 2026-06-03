import type {
  RuntimeAuditNewsItem,
  RuntimeAuditNewsListResponse,
  RuntimeAuditNewsStatus,
  RuntimeAuditQueryParams,
} from '../types';
import { sanitizeRuntimeAuditDetails } from './runtime-audit-sanitize';

const generatedAt = '2026-06-03T02:30:00.000Z';

const items: RuntimeAuditNewsItem[] = [
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
    content_preview: 'Advanced packaging capacity expands across outsourced semiconductor assembly and test vendors.',
    current_stage: 'route_decided',
    first_captured_at: '2026-06-02T07:01:00.000Z',
    focus_stage: 'route_decided',
    last_captured_at: '2026-06-02T07:01:02.000Z',
    published_at: '2026-06-02T07:00:00.000Z',
    raw_event_id: 'rawevt-runtime-002',
    safe_details: sanitizeRuntimeAuditDetails({
      capture_count: 1,
      duplicate_capture_count: 1,
      metadata: { feed: 'advanced-packaging', source: 'Packaging Daily' },
      raw_payload: { secret: 'must-redact' },
    }) ?? {},
    source_name: 'Packaging Daily',
    source_plugin_id: 'quantagent.official.source.rss',
    status: 'routed',
    timeline: [
      step('captured', '采集', 'success', '2026-06-02T07:01:00.000Z', '新闻已由 source plugin 捕获。'),
      step('persisted', 'RawEvent 入库', 'success', '2026-06-02T07:01:03.000Z', '采集事实已作为 RawEvent 保存。'),
      step('scheduler_linked', '调度关联', 'pending', '2026-06-02T07:01:00.000Z', '已有 capture ledger，但没有可关联的 scheduler run。'),
      step('ai_intake_routed', 'AI intake', 'success', '2026-06-02T07:02:00.000Z', 'Router Agent 已完成结构化 intake，decision=route。'),
      step('route_decided', '路由结果', 'success', '2026-06-02T07:02:00.000Z', 'Router Agent 已路由到 semiconductor。'),
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
    safe_details: sanitizeRuntimeAuditDetails({
      capture_count: 1,
      dedupe_strategy: 'canonical_url',
      duplicate_capture_count: 0,
      metadata: { feed: 'memory', source: 'SemiWire' },
      scheduler: { captured_count: 1, duration_ms: 5000, status: 'succeeded', trigger_type: 'scheduled' },
    }) ?? {},
    source_name: 'SemiWire',
    source_plugin_id: 'quantagent.official.source.rss',
    status: 'linked',
    timeline: [
      step('captured', '采集', 'success', '2026-06-01T09:00:01.000Z', '新闻已由 source plugin 捕获。'),
      step('persisted', 'RawEvent 入库', 'success', '2026-06-01T09:00:03.000Z', '采集事实已作为 RawEvent 保存。'),
      step('scheduler_linked', '调度关联', 'success', '2026-06-01T09:00:00.000Z', '关联 scheduler run，状态为 succeeded。'),
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

export function createRuntimeAuditFixtureResponse(): RuntimeAuditNewsListResponse {
  return {
    generated_at: generatedAt,
    items,
    next_cursor: null,
  };
}

export function filterRuntimeAuditFixtureResponse(
  response: RuntimeAuditNewsListResponse,
  params: RuntimeAuditQueryParams,
): RuntimeAuditNewsListResponse {
  const normalized = normalizeRuntimeAuditParams(params);
  const filteredItems = response.items.filter((item) => {
    if (normalized.binding_id && item.trace.binding_id !== normalized.binding_id) return false;
    if (normalized.current_stage && item.current_stage !== normalized.current_stage && item.focus_stage !== normalized.current_stage) return false;
    if (normalized.keyword && !matchesKeyword(item, normalized.keyword)) return false;
    if (normalized.request_id && item.trace.request_id !== normalized.request_id) return false;
    if (normalized.source_plugin_id && item.source_plugin_id !== normalized.source_plugin_id) return false;
    if (normalized.status && item.status !== normalized.status) return false;
    if (normalized.time_from && isBeforeRuntimeAuditTime(item.published_at ?? item.last_captured_at, normalized.time_from)) return false;
    if (normalized.time_to && isAfterRuntimeAuditTime(item.published_at ?? item.last_captured_at, normalized.time_to)) return false;
    if (normalized.trace_id && item.trace.trace_id !== normalized.trace_id) return false;
    return true;
  });

  return {
    ...response,
    items: filteredItems,
  };
}

export function normalizeRuntimeAuditParams(
  params: RuntimeAuditQueryParams,
): RuntimeAuditQueryParams {
  return {
    binding_id: normalizeRuntimeAuditText(params.binding_id),
    current_stage: params.current_stage,
    keyword: normalizeRuntimeAuditText(params.keyword),
    request_id: normalizeRuntimeAuditText(params.request_id),
    source_plugin_id: normalizeRuntimeAuditText(params.source_plugin_id),
    status: normalizeRuntimeAuditStatus(params.status),
    time_from: normalizeRuntimeAuditTime(params.time_from),
    time_to: normalizeRuntimeAuditTime(params.time_to),
    trace_id: normalizeRuntimeAuditText(params.trace_id),
  };
}

function step(
  stepId: RuntimeAuditNewsItem['timeline'][number]['step_id'],
  label: string,
  status: RuntimeAuditNewsItem['timeline'][number]['status'],
  occurredAt: string | null,
  summary: string,
): RuntimeAuditNewsItem['timeline'][number] {
  return {
    label,
    occurred_at: occurredAt,
    refs: [],
    status,
    step_id: stepId,
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
}): RuntimeAuditNewsItem['agent_stages'][number] {
  const outputJson = {
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
      bullet_summary: ['OSAT 和先进封装产能扩张。', 'HBM/AI 加速器相关封装需求仍是主要驱动。'],
      event_type: 'capacity_expansion',
      entities: ['OSAT', 'advanced packaging'],
      companies: [],
      tickers: [],
      technologies: ['advanced packaging', 'CoWoS'],
      products: ['AI accelerator package'],
      locations: [],
      numbers: [],
      time_horizon: 'near_term',
      source_facts: ['Advanced packaging capacity expands across outsourced semiconductor assembly and test vendors.'],
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
      evidence_field_refs: ['article.title', 'article.body_excerpt'],
      schema_validation_status: 'valid',
    },
  };

  return {
    agent_name: 'Router Agent',
    agent_type: 'router_agent',
    key_fields: {
      decision: outputJson.decision,
      short_summary: outputJson.structured_news.short_summary,
      relevance: 'semiconductor / direct / 0.91',
      target_topics: outputJson.routing.target_topics,
      priority: outputJson.routing.priority,
      requires_deep_analysis: outputJson.routing.requires_deep_analysis,
      confidence: outputJson.quality.confidence,
      is_spam: outputJson.quality.is_spam,
    },
    output_json: outputJson,
    refs: [{ kind: 'raw_event', id: rawEventId, label: 'RawEvent' }],
    stage_id: 'router_agent',
    status: 'success',
    summary,
    unavailable_reason: null,
  };
}

function routerAgentUnavailableStage(
  rawEventId: string,
  title: string,
): RuntimeAuditNewsItem['agent_stages'][number] {
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

function mainAgentUnavailableStage(rawEventId: string): RuntimeAuditNewsItem['agent_stages'][number] {
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

function normalizeRuntimeAuditText(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}

function normalizeRuntimeAuditStatus(value: RuntimeAuditQueryParams['status']): RuntimeAuditNewsStatus | undefined {
  return value === 'captured' || value === 'linked' || value === 'pending' || value === 'routed' || value === 'unavailable'
    ? value
    : undefined;
}

function normalizeRuntimeAuditTime(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized && Number.isFinite(Date.parse(normalized)) ? normalized : undefined;
}

function matchesKeyword(item: RuntimeAuditNewsItem, keyword: string): boolean {
  const haystack = [
    item.title,
    item.canonical_url,
    item.content_preview,
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(keyword.toLowerCase());
}

function isBeforeRuntimeAuditTime(value: string | null, boundary: string): boolean {
  const current = parseRuntimeAuditTime(value);
  const limit = parseRuntimeAuditTime(boundary);
  return current !== null && limit !== null && current < limit;
}

function isAfterRuntimeAuditTime(value: string | null, boundary: string): boolean {
  const current = parseRuntimeAuditTime(value);
  const limit = parseRuntimeAuditTime(boundary);
  return current !== null && limit !== null && current > limit;
}

function parseRuntimeAuditTime(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }

  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

import type {
  RuntimeAuditHealthSummary,
  RuntimeAuditMessage,
  RuntimeAuditMessageGroup,
  RuntimeAuditMessagesResponse,
  RuntimeAuditQueryParams,
  RuntimeAuditSafeValue,
} from '../types';
import { sanitizeRuntimeAuditDetails } from './runtime-audit-sanitize';

const generatedAt = '2026-06-03T02:30:00.000Z';

const groups: RuntimeAuditMessageGroup[] = [
  {
    group_id: 'audit-router-route-hbm',
    industry: 'semiconductor',
    decision: 'route',
    message_ids: [
      'msg-route-requested',
      'msg-route-context',
      'msg-route-model',
      'msg-route-validated',
      'msg-route-published',
    ],
    occurred_at: '2026-06-03T01:40:12.000Z',
    source_title: 'SK Hynix raises HBM capacity guidance for AI accelerators',
    status: 'success',
    summary: 'Router Agent 判断为半导体直接相关，路由到 memory/hbm topic。',
    trace: {
      analysis_request_id: 'analysis_req_hbm_001',
      binding_id: 'industry.semiconductor.rss.media',
      correlation_id: 'corr_hbm_001',
      event_id: 'evt_hbm_capacity',
      raw_event_id: 'raw_evt_1001',
      request_id: 'req-runtime-1001',
      routed_event_id: 'event_routed_hbm_001',
      source_message_id: 'source_msg_hbm_001',
      trace_id: 'trace_hbm_001',
    },
  },
  {
    group_id: 'audit-router-discard-phone',
    industry: 'semiconductor',
    decision: 'discard',
    message_ids: [
      'msg-discard-requested',
      'msg-discard-model',
      'msg-discard-validated',
    ],
    occurred_at: '2026-06-03T01:18:44.000Z',
    source_title: 'Generic smartphone accessory roundup repeats affiliate listings',
    status: 'success',
    summary: 'Router Agent 识别为低信息量 SEO 聚合内容，终止深度分析。',
    trace: {
      analysis_request_id: 'analysis_req_noise_001',
      binding_id: 'industry.semiconductor.rss.google-news',
      correlation_id: 'corr_noise_001',
      event_id: 'evt_accessory_noise',
      request_id: 'req-runtime-1002',
      source_message_id: 'source_msg_noise_001',
      trace_id: 'trace_noise_001',
    },
  },
  {
    group_id: 'audit-router-review-capex',
    industry: 'semiconductor',
    decision: 'review',
    message_ids: [
      'msg-review-requested',
      'msg-review-context',
      'msg-review-validated',
      'msg-review-required',
    ],
    occurred_at: '2026-06-03T00:52:09.000Z',
    source_title: 'Hyperscaler capex outlook mixed after data-center lease update',
    status: 'warning',
    summary: '间接影响 AI 服务器与内存需求，但置信度不足，进入人工复核。',
    trace: {
      analysis_request_id: 'analysis_req_review_001',
      binding_id: 'industry.semiconductor.rss.media',
      correlation_id: 'corr_review_001',
      event_id: 'evt_capex_review',
      request_id: 'req-runtime-1003',
      source_message_id: 'source_msg_review_001',
      trace_id: 'trace_review_001',
    },
  },
  {
    group_id: 'audit-router-degraded-rss',
    industry: 'semiconductor',
    decision: 'route',
    message_ids: [
      'msg-degraded-requested',
      'msg-degraded-context',
      'msg-degraded-validated',
      'msg-degraded-published',
    ],
    occurred_at: '2026-06-02T23:49:31.000Z',
    source_title: 'Foundry utilization commentary points to advanced packaging bottleneck',
    status: 'warning',
    summary: 'Readability 失败后使用 RSS 摘要降级分析，仍路由到 advanced-packaging。',
    trace: {
      analysis_request_id: 'analysis_req_degraded_001',
      binding_id: 'industry.semiconductor.rss.media',
      correlation_id: 'corr_degraded_001',
      event_id: 'evt_packaging_degraded',
      request_id: 'req-runtime-1004',
      routed_event_id: 'event_routed_degraded_001',
      source_message_id: 'source_msg_degraded_001',
      trace_id: 'trace_degraded_001',
    },
  },
  {
    group_id: 'audit-router-schema-invalid',
    industry: 'semiconductor',
    message_ids: [
      'msg-invalid-requested',
      'msg-invalid-model',
      'msg-invalid-failed',
    ],
    occurred_at: '2026-06-02T23:12:17.000Z',
    source_title: 'Memory channel note missing structured model output',
    status: 'error',
    summary: '模型输出未通过 EventIntakeDecisionV1 校验，没有静默进入 route。',
    trace: {
      analysis_request_id: 'analysis_req_invalid_001',
      binding_id: 'industry.semiconductor.rss.analyst',
      correlation_id: 'corr_invalid_001',
      event_id: 'evt_schema_invalid',
      request_id: 'req-runtime-1005',
      source_message_id: 'source_msg_invalid_001',
      trace_id: 'trace_invalid_001',
    },
  },
];

const messages: RuntimeAuditMessage[] = [
  message('msg-route-requested', 'audit-router-route-hbm', 'source', 'analysis_requested', 'success', '收到 industry.analysis.requested', 'RSS 捕获事实已完成，worker 将半导体 owner 的文章送入 AI intake。', '2026-06-03T01:40:12.000Z', ['industry.analysis.requested'], { topic: 'industry.analysis.requested', owner: 'industry:semiconductor' }),
  message('msg-route-context', 'audit-router-route-hbm', 'worker', 'context_built', 'success', '构建 IndustryEventContextV1', '正文在预算内，包含 HBM、AI accelerator、capacity guidance 等直接半导体信号。', '2026-06-03T01:40:13.000Z', ['article.title', 'quality.content_completeness'], { content_completeness: 'full', max_body_chars: 24000 }),
  message('msg-route-model', 'audit-router-route-hbm', 'model', 'model_invoked', 'success', '执行 single-call 结构化 intake', '模型只调用一次，无 tool call，无二次抓取。', '2026-06-03T01:40:15.000Z', ['budget.single_call'], { model: 'configured-router-model', prompt_tokens: 1840, completion_tokens: 620 }),
  message('msg-route-validated', 'audit-router-route-hbm', 'agent', 'decision_validated', 'success', '决策校验通过：route', 'direct relevance 0.92，目标 industries: semiconductor，topics: memory/hbm。', '2026-06-03T01:40:18.000Z', ['decision', 'routing.target_topics'], {
    decision: 'route',
    industry_relevance: [{ industry_id: 'semiconductor', relationship: 'direct', relevance_score: 0.92 }],
    routing: { priority: 'high', target_industries: ['semiconductor'], target_topics: ['memory', 'hbm'] },
  }, 'route', 'high'),
  message('msg-route-published', 'audit-router-route-hbm', 'event_bus', 'event_routed_published', 'success', '发布 event.routed', '结构化路由结果已发布，等待下游行业分析消费。', '2026-06-03T01:40:19.000Z', ['event.routed'], { topic: 'event.routed', routed_event_id: 'event_routed_hbm_001' }, 'route', 'high'),

  message('msg-discard-requested', 'audit-router-discard-phone', 'source', 'analysis_requested', 'success', '收到低价值候选文章', 'Google News 扩展源捕获到泛消费电子聚合内容。', '2026-06-03T01:18:44.000Z', ['source.source_tier'], { source_tier: 'optional', topic: 'industry.analysis.requested' }),
  message('msg-discard-model', 'audit-router-discard-phone', 'model', 'model_invoked', 'success', '执行 single-call 过滤', '模型判断缺少行业事实，命中 low_information 和 SEO noise。', '2026-06-03T01:18:46.000Z', ['quality.noise_flags'], { noise_flags: ['seo_noise', 'affiliate_roundup'], confidence: 0.88 }),
  message('msg-discard-validated', 'audit-router-discard-phone', 'agent', 'discarded', 'success', '决策校验通过：discard', 'discard_reason=low_information，requires_deep_analysis=false，节省后续行业分析 token。', '2026-06-03T01:18:47.000Z', ['discard_reason', 'routing.requires_deep_analysis'], { decision: 'discard', discard_reason: 'low_information', requires_deep_analysis: false }, 'discard', 'low'),

  message('msg-review-requested', 'audit-router-review-capex', 'source', 'analysis_requested', 'success', '收到间接相关候选文章', '文章讨论 hyperscaler capex 与数据中心租约，可能影响 AI server demand。', '2026-06-03T00:52:09.000Z', ['article.title'], { topic: 'industry.analysis.requested' }),
  message('msg-review-context', 'audit-router-review-capex', 'worker', 'context_built', 'success', '保留间接相关行业上下文', 'context 中包含 AI infrastructure、memory bandwidth、GPU supply chain 等 indirect scope terms。', '2026-06-03T00:52:10.000Z', ['industry_candidates.indirect_scope_terms'], { relationship: 'indirect', indirect_scope_terms: ['AI server demand', 'data-center buildout'] }),
  message('msg-review-validated', 'audit-router-review-capex', 'agent', 'decision_validated', 'warning', '决策校验通过：review', 'relevance_score=0.58，低于 route threshold，但不能直接丢弃。', '2026-06-03T00:52:14.000Z', ['industry_relevance.relevance_score'], { decision: 'review', confidence: 0.58, reason: 'indirect impact requires analyst check' }, 'review', 'normal'),
  message('msg-review-required', 'audit-router-review-capex', 'system', 'review_requested', 'warning', '进入复核队列', '该 item 暂不进入深度行业分析，等待更低成本人工或策略复核。', '2026-06-03T00:52:15.000Z', ['routing.requires_human_review'], { requires_human_review: true }, 'review', 'normal'),

  message('msg-degraded-requested', 'audit-router-degraded-rss', 'source', 'analysis_requested', 'success', '收到 RSS summary-only 输入', 'Readability enrichment 失败，但 RSS 标题和摘要仍可分析。', '2026-06-02T23:49:31.000Z', ['source.enrichment_status'], { enrichment_status: 'failed_degraded', degraded_reason: 'readability_timeout' }, undefined, undefined, ['degraded', 'rss_summary_only']),
  message('msg-degraded-context', 'audit-router-degraded-rss', 'worker', 'context_built', 'warning', '构建降级 context', 'context 标记 content_completeness=rss_summary_only，未伪装完整正文。', '2026-06-02T23:49:32.000Z', ['article.content_completeness'], { content_completeness: 'rss_summary_only', body_content_available: false }, undefined, undefined, ['degraded', 'rss_summary_only']),
  message('msg-degraded-validated', 'audit-router-degraded-rss', 'agent', 'decision_validated', 'warning', '降级输入仍可 route', 'foundry utilization 与 advanced packaging bottleneck 直接相关，但保留 degraded 标记。', '2026-06-02T23:49:36.000Z', ['quality.enrichment_status', 'routing.target_topics'], { decision: 'route', target_topics: ['advanced-packaging'], enrichment_status: 'failed_degraded' }, 'route', 'normal', ['degraded', 'rss_summary_only']),
  message('msg-degraded-published', 'audit-router-degraded-rss', 'event_bus', 'event_routed_published', 'warning', '发布带降级标记的 event.routed', '下游可区分该路由结果来自 RSS 摘要，而不是完整正文。', '2026-06-02T23:49:37.000Z', ['event.routed.quality.enrichment_status'], { topic: 'event.routed', enrichment_status: 'failed_degraded' }, 'route', 'normal', ['degraded', 'rss_summary_only']),

  message('msg-invalid-requested', 'audit-router-schema-invalid', 'source', 'analysis_requested', 'success', '收到分析请求', '候选文章进入 Router Agent intake。', '2026-06-02T23:12:17.000Z', ['industry.analysis.requested'], { topic: 'industry.analysis.requested' }),
  message('msg-invalid-model', 'audit-router-schema-invalid', 'model', 'model_invoked', 'error', '模型返回无效结构', '返回内容缺少 decision 字段，未通过 EventIntakeDecisionV1 校验。', '2026-06-02T23:12:20.000Z', ['schema_validation_status'], { schema_validation_status: 'failed', provider_raw_response: '{...redacted...}' }, undefined, undefined, ['schema_invalid', 'partial_unavailable']),
  message('msg-invalid-failed', 'audit-router-schema-invalid', 'agent', 'failed', 'error', 'Schema validation failure', '系统记录 safe error summary，没有静默 route 到深度行业分析。', '2026-06-02T23:12:21.000Z', ['safe_error_summary'], { safe_error_summary: 'missing required field: decision' }, undefined, undefined, ['schema_invalid', 'provider_failed']),
].map((item) => ({ ...item, safe_details: sanitizeRuntimeAuditDetails(item.safe_details) }));

export function createRuntimeAuditFixtureResponse(): RuntimeAuditMessagesResponse {
  const health: RuntimeAuditHealthSummary = {
    generated_at: generatedAt,
    label: 'Fixture audit read model',
    partial_unavailable_count: messages.filter((item) => item.badges.includes('partial_unavailable')).length,
    status: 'degraded',
    total_groups: groups.length,
  };

  return {
    fixture_mode: true,
    generated_at: generatedAt,
    groups,
    health,
    messages,
  };
}

export function filterRuntimeAuditFixtureResponse(
  response: RuntimeAuditMessagesResponse,
  params: RuntimeAuditQueryParams,
): RuntimeAuditMessagesResponse {
  const normalized = normalizeRuntimeAuditParams(params);
  const filteredGroups = response.groups.filter((group) => {
    if (normalized.decision && group.decision !== normalized.decision) return false;
    if (normalized.status && group.status !== normalized.status) return false;
    if (normalized.industry && !group.industry.toLowerCase().includes(normalized.industry)) return false;
    if (normalized.event_id && !group.trace.event_id?.toLowerCase().includes(normalized.event_id)) return false;
    if (normalized.trace_id && !group.trace.trace_id?.toLowerCase().includes(normalized.trace_id)) return false;
    if (normalized.time_from && isBeforeRuntimeAuditTime(group.occurred_at, normalized.time_from)) return false;
    if (normalized.time_to && isAfterRuntimeAuditTime(group.occurred_at, normalized.time_to)) return false;
    return true;
  });
  const allowedGroupIds = new Set(filteredGroups.map((group) => group.group_id));
  const filteredMessages = response.messages.filter((message) => allowedGroupIds.has(message.group_id));

  return {
    ...response,
    groups: filteredGroups,
    health: {
      ...response.health,
      total_groups: filteredGroups.length,
    },
    messages: filteredMessages,
  };
}

export function normalizeRuntimeAuditParams(
  params: RuntimeAuditQueryParams,
): RuntimeAuditQueryParams {
  return {
    decision: normalizeRuntimeAuditDecision(params.decision),
    event_id: normalizeRuntimeAuditText(params.event_id),
    industry: normalizeRuntimeAuditText(params.industry),
    status: normalizeRuntimeAuditStatus(params.status),
    time_from: normalizeRuntimeAuditTime(params.time_from),
    time_to: normalizeRuntimeAuditTime(params.time_to),
    trace_id: normalizeRuntimeAuditText(params.trace_id),
  };
}

function normalizeRuntimeAuditText(value: string | undefined): string | undefined {
  const normalized = value?.trim().toLowerCase();
  return normalized || undefined;
}

function normalizeRuntimeAuditDecision(
  value: RuntimeAuditQueryParams['decision'],
): RuntimeAuditQueryParams['decision'] | undefined {
  const normalized = normalizeRuntimeAuditText(value);
  return normalized === 'discard' || normalized === 'review' || normalized === 'route'
    ? normalized
    : undefined;
}

function normalizeRuntimeAuditStatus(
  value: RuntimeAuditQueryParams['status'],
): RuntimeAuditQueryParams['status'] | undefined {
  const normalized = normalizeRuntimeAuditText(value);
  return normalized === 'error' ||
    normalized === 'pending' ||
    normalized === 'success' ||
    normalized === 'unavailable' ||
    normalized === 'warning'
    ? normalized
    : undefined;
}

function normalizeRuntimeAuditTime(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized && Number.isFinite(Date.parse(normalized)) ? normalized : undefined;
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

function message(
  id: string,
  groupId: string,
  actorType: RuntimeAuditMessage['actor_type'],
  stage: RuntimeAuditMessage['stage'],
  status: RuntimeAuditMessage['status'],
  title: string,
  summary: string,
  occurredAt: string,
  evidenceFields: string[],
  safeDetails: Record<string, RuntimeAuditSafeValue>,
  decision?: RuntimeAuditMessage['decision'],
  priority?: RuntimeAuditMessage['priority'],
  badges: RuntimeAuditMessage['badges'] = [],
): RuntimeAuditMessage {
  const group = groups.find((item) => item.group_id === groupId);
  if (!group) {
    throw new Error(`Missing runtime audit fixture group ${groupId}`);
  }

  return {
    actor_type: actorType,
    badges,
    decision,
    evidence_refs: evidenceFields.map((field) => ({ field_path: field, label: field })),
    group_id: groupId,
    id,
    occurred_at: occurredAt,
    priority,
    related_refs: buildRelatedRefs(group),
    safe_details: safeDetails,
    stage,
    status,
    summary,
    title,
    trace: group.trace,
  };
}

function buildRelatedRefs(group: RuntimeAuditMessageGroup): RuntimeAuditMessage['related_refs'] {
  const refs: RuntimeAuditMessage['related_refs'] = [
    { kind: 'event_topic', id: 'industry.analysis.requested', label: 'industry.analysis.requested' },
  ];
  if (group.decision === 'route') {
    refs.push({ kind: 'event_topic', id: 'event.routed', label: 'event.routed' });
  }
  return refs;
}

import type {
  RuntimeAuditActorType,
  RuntimeAuditBadge,
  RuntimeAuditDecision,
  RuntimeAuditPriority,
  RuntimeAuditStage,
  RuntimeAuditStatus,
} from '../types';

export function formatRuntimeAuditDecision(value: RuntimeAuditDecision): string {
  const labels: Record<RuntimeAuditDecision, string> = {
    discard: '丢弃',
    review: '复核',
    route: '路由',
  };
  return labels[value];
}

export function formatRuntimeAuditStatus(value: RuntimeAuditStatus): string {
  const labels: Record<RuntimeAuditStatus, string> = {
    error: '错误',
    pending: '等待',
    success: '成功',
    unavailable: '不可用',
    warning: '警告',
  };
  return labels[value];
}

export function formatRuntimeAuditStage(value: RuntimeAuditStage): string {
  const labels: Record<RuntimeAuditStage, string> = {
    analysis_requested: '收到分析请求',
    context_built: '构建上下文',
    decision_validated: '校验决策',
    discarded: '终止深度分析',
    event_routed_published: '发布路由事件',
    failed: '失败',
    model_invoked: '模型调用',
    review_requested: '进入复核',
  };
  return labels[value];
}

export function formatRuntimeAuditActor(value: RuntimeAuditActorType): string {
  const labels: Record<RuntimeAuditActorType, string> = {
    agent: 'Agent',
    event_bus: 'Event Bus',
    model: 'Model',
    source: 'Source',
    system: 'System',
    worker: 'Worker',
  };
  return labels[value];
}

export function formatRuntimeAuditBadge(value: RuntimeAuditBadge): string {
  const labels: Record<RuntimeAuditBadge, string> = {
    degraded: '降级输入',
    partial_unavailable: '局部不可用',
    provider_failed: '模型失败',
    rss_summary_only: 'RSS 摘要',
    schema_invalid: 'Schema 无效',
  };
  return labels[value];
}

export function formatRuntimeAuditPriority(value: RuntimeAuditPriority): string {
  const labels: Record<RuntimeAuditPriority, string> = {
    high: '高',
    low: '低',
    normal: '正常',
    urgent: '紧急',
  };
  return labels[value];
}

export function formatRuntimeAuditDate(value: string | null): string {
  if (!value) return '未记录时间';
  return new Date(value).toLocaleString();
}

export function getRuntimeAuditStatusTone(value: RuntimeAuditStatus): string {
  const tones: Record<RuntimeAuditStatus, string> = {
    error: 'border-trading-down/30 bg-trading-down/6 text-trading-down',
    pending: 'border-info/25 bg-info/6 text-info',
    success: 'border-trading-up/25 bg-trading-up/8 text-trading-up',
    unavailable: 'border-hairline bg-surface-card text-muted-strong',
    warning: 'border-amber-200 bg-amber-50 text-amber-700',
  };
  return tones[value];
}

export function getRuntimeAuditDecisionTone(value: RuntimeAuditDecision): string {
  const tones: Record<RuntimeAuditDecision, string> = {
    discard: 'border-hairline bg-surface-card text-muted-strong',
    review: 'border-amber-200 bg-amber-50 text-amber-700',
    route: 'border-trading-up/25 bg-trading-up/8 text-trading-up',
  };
  return tones[value];
}

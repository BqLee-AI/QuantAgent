import type {
  RuntimeAuditAgentStageStatus,
  RuntimeAuditAgentType,
  RuntimeAuditNewsStage,
  RuntimeAuditNewsStatus,
  RuntimeAuditTimelineStatus,
} from '../types';

export function formatRuntimeAuditStatus(
  value: RuntimeAuditAgentStageStatus | RuntimeAuditNewsStatus | RuntimeAuditTimelineStatus,
): string {
  const labels: Record<RuntimeAuditAgentStageStatus | RuntimeAuditNewsStatus | RuntimeAuditTimelineStatus, string> = {
    captured: '已采集',
    failed: '失败',
    linked: '已关联调度',
    pending: '等待',
    routed: '已路由',
    success: '成功',
    unavailable: '不可用',
    warning: '需注意',
  };
  return labels[value];
}

export function formatRuntimeAuditStage(value: RuntimeAuditNewsStage): string {
  const labels: Record<RuntimeAuditNewsStage, string> = {
    ai_intake_unavailable: 'AI intake 暂不可审计',
    ai_intake_routed: 'AI intake 已审计',
    captured: '采集',
    persisted: 'RawEvent 入库',
    route_decided: '路由结果已审计',
    route_unavailable: '路由结果暂不可审计',
    scheduler_linked: '调度关联',
  };
  return labels[value];
}

export function formatRuntimeAuditDate(value: string | null): string {
  if (!value) return '未记录时间';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function formatRuntimeAuditTimeline(items: readonly { step_id: RuntimeAuditNewsStage }[]): string {
  return items.map((item) => formatRuntimeAuditStage(item.step_id)).join(' -> ');
}

export function formatRuntimeAuditAgentType(value: RuntimeAuditAgentType): string {
  const labels: Record<RuntimeAuditAgentType, string> = {
    industry_main_agent: '行业 MainAgent',
    router_agent: 'Router Agent',
  };
  return labels[value];
}

export function getRuntimeAuditStatusTone(
  value: RuntimeAuditAgentStageStatus | RuntimeAuditNewsStatus | RuntimeAuditTimelineStatus,
): string {
  const tones: Record<RuntimeAuditAgentStageStatus | RuntimeAuditNewsStatus | RuntimeAuditTimelineStatus, string> = {
    captured: 'border-info/25 bg-info/6 text-info',
    failed: 'border-trading-down/25 bg-trading-down/8 text-trading-down',
    linked: 'border-trading-up/25 bg-trading-up/8 text-trading-up',
    pending: 'border-info/25 bg-info/6 text-info',
    routed: 'border-trading-up/25 bg-trading-up/8 text-trading-up',
    success: 'border-trading-up/25 bg-trading-up/8 text-trading-up',
    unavailable: 'border-hairline bg-surface-card text-muted-strong',
    warning: 'border-amber-200 bg-amber-50 text-amber-700',
  };
  return tones[value];
}

export function getRuntimeAuditStageTone(value: RuntimeAuditNewsStage): string {
  if (value.endsWith('_unavailable')) {
    return 'border-hairline bg-surface-card text-muted-strong';
  }
  if (value === 'scheduler_linked' || value === 'ai_intake_routed' || value === 'route_decided') {
    return 'border-trading-up/25 bg-trading-up/8 text-trading-up';
  }
  return 'border-info/25 bg-info/6 text-info';
}

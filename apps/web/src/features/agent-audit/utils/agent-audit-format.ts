import type {
  AgentAuditKeyField,
  AgentAuditKeyFieldState,
  AgentAuditSafeValue,
  AgentAuditStageKind,
  AgentAuditStageStatus,
} from '../types';

export function formatAgentAuditStageKind(value: AgentAuditStageKind): string {
  switch (value) {
    case 'industry_main_agent':
      return '行业 MainAgent';
    case 'policy_gate':
      return 'Policy Gate';
    case 'router_agent':
      return 'Router Agent';
    case 'tool_call':
      return 'Tool Call';
    case 'unknown':
      return '未知 Agent';
    default:
      return value;
  }
}

export function formatAgentAuditStatus(value: AgentAuditStageStatus): string {
  switch (value) {
    case 'failed':
      return '失败';
    case 'masked':
      return '已脱敏';
    case 'pending':
      return '等待';
    case 'skipped':
      return '已跳过';
    case 'success':
      return '成功';
    case 'unavailable':
      return '不可用';
    case 'warning':
      return '需注意';
    default:
      return value;
  }
}

export function getAgentAuditStatusTone(value: AgentAuditStageStatus): string {
  switch (value) {
    case 'failed':
      return 'border-trading-down/25 bg-trading-down/8 text-trading-down';
    case 'masked':
    case 'skipped':
    case 'unavailable':
      return 'border-hairline bg-surface-card text-muted-strong';
    case 'success':
      return 'border-trading-up/25 bg-trading-up/8 text-trading-up';
    case 'warning':
      return 'border-amber-200 bg-amber-50 text-amber-700';
    case 'pending':
    default:
      return 'border-info/25 bg-info/6 text-info';
  }
}

export function formatAgentAuditDate(value: string | null | undefined): string {
  if (!value) return '未记录时间';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function getAgentAuditKeyFieldLabel(key: string, field: AgentAuditKeyField | AgentAuditSafeValue | undefined): string {
  if (isAgentAuditKeyField(field)) return field.label;
  return key;
}

export function getAgentAuditKeyFieldState(field: AgentAuditKeyField | AgentAuditSafeValue | undefined): AgentAuditKeyFieldState {
  if (isAgentAuditKeyField(field)) return field.state ?? (field.value === undefined ? 'unavailable' : 'normal');
  return field === undefined ? 'unavailable' : 'normal';
}

export function getAgentAuditKeyFieldValue(field: AgentAuditKeyField | AgentAuditSafeValue | undefined): AgentAuditSafeValue | undefined {
  if (isAgentAuditKeyField(field)) return field.value;
  return field;
}

export function getAgentAuditKeyFieldDescription(field: AgentAuditKeyField | AgentAuditSafeValue | undefined): string | null {
  if (!isAgentAuditKeyField(field)) return null;
  return field.unavailable_reason ?? field.description ?? null;
}

export function formatAgentAuditFieldValue(value: AgentAuditSafeValue | undefined): string {
  if (value === undefined) return '不可用';
  if (value === null) return 'null';
  if (Array.isArray(value)) return value.map((item) => formatAgentAuditFieldValue(item)).join(', ') || '[]';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function isAgentAuditKeyField(value: AgentAuditKeyField | AgentAuditSafeValue | undefined): value is AgentAuditKeyField {
  return Boolean(
    value
      && typeof value === 'object'
      && !Array.isArray(value)
      && 'label' in value
      && 'value' in value,
  );
}

import type { AgentAuditSafeValue } from '../types';
import { sanitizeAgentAuditJson } from '../utils';

interface AgentJsonViewProps {
  value?: Record<string, AgentAuditSafeValue> | null;
}

export function AgentJsonView({ value }: AgentJsonViewProps) {
  const sanitizedValue = sanitizeAgentAuditJson(value);

  if (!sanitizedValue) {
    return (
      <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-3 text-body-sm text-muted">
        当前没有持久化结构化 output JSON。
      </div>
    );
  }

  return (
    <pre className="max-h-[26rem] overflow-auto rounded-lg border border-hairline bg-ink px-3 py-3 text-[12px] leading-5 text-canvas">
      {JSON.stringify(sanitizedValue, null, 2)}
    </pre>
  );
}

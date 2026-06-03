import type { RuntimeAuditSafeValue } from '../../types';

interface RuntimeAuditAgentJsonViewProps {
  value: Record<string, RuntimeAuditSafeValue> | null;
}

export function RuntimeAuditAgentJsonView({ value }: RuntimeAuditAgentJsonViewProps) {
  if (!value) {
    return (
      <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-3 text-body-sm text-muted">
        当前没有持久化结构化 output JSON。
      </div>
    );
  }

  return (
    <pre className="max-h-[26rem] overflow-auto rounded-lg border border-hairline bg-ink px-3 py-3 text-[12px] leading-5 text-canvas">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

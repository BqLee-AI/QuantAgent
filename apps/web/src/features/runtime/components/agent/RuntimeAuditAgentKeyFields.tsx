import type { RuntimeAuditSafeValue } from '../../types';

interface RuntimeAuditAgentKeyFieldsProps {
  fields: Record<string, RuntimeAuditSafeValue>;
}

export function RuntimeAuditAgentKeyFields({ fields }: RuntimeAuditAgentKeyFieldsProps) {
  const entries = Object.entries(fields).filter(([, value]) => value !== undefined);

  if (entries.length === 0) {
    return (
      <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
        当前阶段没有可展示的关键字段。
      </p>
    );
  }

  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
          <dt className="text-[11px] font-semibold uppercase tracking-normal text-muted">{key}</dt>
          <dd className="m-0 mt-1 break-words text-body-sm font-semibold text-ink">{formatAgentFieldValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function formatAgentFieldValue(value: RuntimeAuditSafeValue): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return value.map((item) => formatAgentFieldValue(item)).join(', ') || '[]';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

import type { RuntimeAuditSafeValue } from '../../types';

interface RuntimeAuditSafeDetailsProps {
  details: Record<string, RuntimeAuditSafeValue> | null;
}

export function RuntimeAuditSafeDetails({ details }: RuntimeAuditSafeDetailsProps) {
  if (!details || Object.keys(details).length === 0) {
    return <p className="m-0 text-body-sm text-muted">该节点没有可展示的安全详情。</p>;
  }

  return (
    <dl className="grid gap-3">
      {Object.entries(details).map(([key, value]) => (
        <div key={key} className="grid gap-1 rounded-lg border border-hairline bg-surface-soft px-3 py-2">
          <dt className="text-[12px] font-semibold text-muted-strong">{key}</dt>
          <dd className="m-0 break-words font-mono text-[12px] leading-5 text-ink">
            {formatSafeValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function formatSafeValue(value: RuntimeAuditSafeValue): string {
  if (value === null) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value, null, 2);
}

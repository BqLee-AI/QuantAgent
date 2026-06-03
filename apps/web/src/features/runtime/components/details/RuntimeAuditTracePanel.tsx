import type { RuntimeAuditNewsTrace } from '../../types';

interface RuntimeAuditTracePanelProps {
  trace: RuntimeAuditNewsTrace;
}

export function RuntimeAuditTracePanel({ trace }: RuntimeAuditTracePanelProps) {
  const rows = Object.entries(trace).filter(([, value]) => Boolean(value));

  return (
    <dl className="grid gap-2">
      {rows.map(([key, value]) => (
        <div key={key} className="grid gap-0.5">
          <dt className="text-[11px] font-semibold uppercase text-muted">{key}</dt>
          <dd className="m-0 break-all font-mono text-[12px] text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

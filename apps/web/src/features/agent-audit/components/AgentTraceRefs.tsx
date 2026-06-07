import type { AgentAuditTraceRef } from '../types';

interface AgentTraceRefsProps {
  refs: AgentAuditTraceRef[];
}

export function AgentTraceRefs({ refs }: AgentTraceRefsProps) {
  if (refs.length === 0) {
    return (
      <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
        当前阶段没有可审计引用。
      </p>
    );
  }

  return (
    <div className="grid gap-2">
      {refs.map((ref) => {
        const body = `${ref.kind}:${ref.id}`;
        return (
          <div key={`${ref.kind}:${ref.id}`} className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-normal text-muted">{ref.label}</div>
            {ref.href ? (
              <a className="break-all font-mono text-[12px] text-info" href={ref.href} rel="noreferrer" target="_blank">
                {body}
              </a>
            ) : (
              <div className="break-all font-mono text-[12px] text-muted">{body}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

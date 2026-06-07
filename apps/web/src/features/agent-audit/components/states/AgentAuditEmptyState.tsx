interface AgentAuditEmptyStateProps {
  message: string;
  title?: string;
}

export function AgentAuditEmptyState({ message, title }: AgentAuditEmptyStateProps) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
      {title ? <div className="mb-1 font-semibold text-ink">{title}</div> : null}
      <p className="m-0">{message}</p>
    </div>
  );
}

export function RuntimeAuditEmptyState() {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-8 text-center">
      <p className="m-0 text-title-sm font-semibold text-ink">没有匹配的审计消息</p>
      <p className="m-0 mt-2 text-body-sm text-muted">
        当前筛选没有命中 Router Agent 样例。清空筛选后可查看 route、discard、review、degraded 和 schema invalid。
      </p>
    </div>
  );
}

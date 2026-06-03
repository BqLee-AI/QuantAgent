export function RuntimeAuditEmptyState() {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-8 text-center">
      <p className="m-0 text-title-sm font-semibold text-ink">没有匹配的新闻审计项</p>
      <p className="m-0 mt-2 text-body-sm text-muted">
        当前筛选没有命中 RawEvent 新闻。清空筛选，或先运行 scheduler/worker 抓取 RSS 数据。
      </p>
    </div>
  );
}

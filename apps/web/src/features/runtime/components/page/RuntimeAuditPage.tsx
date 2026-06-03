import type { RuntimeAuditFilters } from '../../types';
import { useRuntimeAuditPage } from '../../hooks';
import { RuntimeAuditConversation } from '../conversation/RuntimeAuditConversation';
import { RuntimeAuditDetailDrawer } from '../details/RuntimeAuditDetailDrawer';
import { RuntimeAuditFilterBar } from '../filters/RuntimeAuditFilterBar';
import { RuntimeCompactHealthStrip } from '../health/RuntimeCompactHealthStrip';
import { RuntimeAuditErrorState } from '../states/RuntimeAuditErrorState';
import { RuntimeAuditLoadingState } from '../states/RuntimeAuditLoadingState';
import { RuntimeAuditPermissionState } from '../states/RuntimeAuditPermissionState';

interface RuntimeAuditPageProps {
  search?: Partial<RuntimeAuditFilters>;
}

export function RuntimeAuditPage({ search }: RuntimeAuditPageProps) {
  const page = useRuntimeAuditPage(search);

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="page-header">
          <p className="page-kicker">Runtime</p>
          <h1 className="page-title">Runtime 审计</h1>
          <p className="page-description">
            按新闻 RawEvent 审计采集、入库、调度关联与当前缺失的 AI/路由持久化事实。
          </p>
        </div>
        <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
          列表和默认详情不返回完整正文或 raw payload；需要正文时从 RawEvent 详情按 ID 获取。
        </div>
      </section>

      <RuntimeCompactHealthStrip
        health={page.health}
        isRefreshing={page.auditQuery.isFetching}
        onRefresh={() => {
          void page.auditQuery.refetch();
        }}
      />

      <RuntimeAuditFilterBar
        filters={page.filters}
        onReset={page.resetFilters}
        onUpdate={page.updateFilter}
      />

      {page.auditQuery.isLoading ? <RuntimeAuditLoadingState /> : null}
      {page.auditQuery.isError ? (
        page.isPermissionDenied ? (
          <RuntimeAuditPermissionState error={page.auditQuery.error} />
        ) : (
          <RuntimeAuditErrorState
            error={page.auditQuery.error}
            onRetry={() => {
              void page.auditQuery.refetch();
            }}
          />
        )
      ) : null}

      {!page.auditQuery.isLoading && !page.auditQuery.isError ? (
        <section className="grid gap-4 xl:grid-cols-[minmax(300px,360px)_minmax(0,1fr)]">
          <RuntimeAuditConversation
            items={page.items}
            selectedRawEventId={page.selection.selectedRawEventId}
            onSelectNews={page.selection.setSelectedRawEventId}
          />
          <RuntimeAuditDetailDrawer
            item={page.selection.selectedNews}
          />
        </section>
      ) : null}
    </div>
  );
}

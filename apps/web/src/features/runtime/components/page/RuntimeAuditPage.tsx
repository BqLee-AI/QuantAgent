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
            以 Router Agent 为首个样例，按消息流回放一次事件从 source request、AI intake 到 event.routed 的判断过程。
          </p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-body-sm text-amber-700">
          受控 fixture 样例；生产审计 read model 尚未在本 change 中声明完成。
        </div>
      </section>

      <RuntimeCompactHealthStrip
        health={page.health}
        isFixtureMode={page.isFixtureMode}
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
        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,380px)]">
          <RuntimeAuditConversation
            groups={page.groups}
            messages={page.messages}
            selectedMessageId={page.selection.selectedMessageId}
            onSelectMessage={page.selection.setSelectedMessageId}
          />
          <RuntimeAuditDetailDrawer
            group={page.selection.selectedGroup}
            message={page.selection.selectedMessage}
          />
        </section>
      ) : null}
    </div>
  );
}

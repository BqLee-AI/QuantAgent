import { Chip } from "@heroui/react";

import type { RuntimeDashboardFilters as RuntimeDashboardSearchFilters } from "../../types";
import { useRuntimeDashboardPage } from "../../hooks";
import { AgentRunListPanel } from "../agent-runs/AgentRunListPanel";
import { RuntimeDashboardFilters as RuntimeDashboardFilterForm } from "../filters/RuntimeDashboardFilters";
import { RuntimeHealthPanel } from "../health/RuntimeHealthPanel";
import { RuntimeErrorListPanel } from "../runtime-errors/RuntimeErrorListPanel";
import { SchedulerRunListPanel } from "../scheduler-runs/SchedulerRunListPanel";
import { ToolInvocationListPanel } from "../tool-invocations/ToolInvocationListPanel";

interface RuntimeDashboardPageProps {
  search: Partial<RuntimeDashboardSearchFilters>;
}

export function RuntimeDashboardPage({ search }: RuntimeDashboardPageProps) {
  const page = useRuntimeDashboardPage(search);

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
            Runtime
          </p>
          <h1 className="m-0 mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
            运行态观察
          </h1>
          <p className="m-0 mt-2 max-w-[72ch] text-sm leading-6 text-muted">
            只读查看 health、AgentRun、ToolInvocation、SchedulerRun 和
            RuntimeError。页面不提供调度控制，也不展示 raw prompt、完整推理链或未脱敏载荷。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip size="sm" variant="soft">
            REST snapshot
          </Chip>
          <Chip size="sm" variant="soft">
            read-only
          </Chip>
          {page.partialUnavailableCount > 0 ? (
            <Chip color="warning" size="sm" variant="soft">
              {page.partialUnavailableCount} 个局部资源降级
            </Chip>
          ) : null}
        </div>
      </section>

      <RuntimeHealthPanel
        data={page.healthQuery.data}
        error={page.healthQuery.error}
        isLoading={page.healthQuery.isLoading}
        isRefreshing={page.isRefreshing}
        onRefresh={page.refreshAll}
      />

      <RuntimeDashboardFilterForm
        draft={page.draft}
        onApply={page.applyFilters}
        onReset={page.resetFilters}
        onUpdate={page.updateDraft}
      />

      <div className="grid gap-5">
        <AgentRunListPanel
          data={page.agentRunsQuery.data}
          error={page.agentRunsQuery.error}
          isLoading={page.agentRunsQuery.isLoading}
          onRetry={() => {
            void page.agentRunsQuery.refetch();
          }}
        />
        <ToolInvocationListPanel
          data={page.toolInvocationsQuery.data}
          error={page.toolInvocationsQuery.error}
          isLoading={page.toolInvocationsQuery.isLoading}
          onRetry={() => {
            void page.toolInvocationsQuery.refetch();
          }}
        />
        <SchedulerRunListPanel
          data={page.schedulerRunsQuery.data}
          error={page.schedulerRunsQuery.error}
          isLoading={page.schedulerRunsQuery.isLoading}
          onRetry={() => {
            void page.schedulerRunsQuery.refetch();
          }}
        />
        <RuntimeErrorListPanel
          data={page.runtimeErrorsQuery.data}
          error={page.runtimeErrorsQuery.error}
          isLoading={page.runtimeErrorsQuery.isLoading}
          onRetry={() => {
            void page.runtimeErrorsQuery.refetch();
          }}
        />
      </div>
    </div>
  );
}

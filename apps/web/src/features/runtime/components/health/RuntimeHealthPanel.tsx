import { Button, Chip } from "@heroui/react";

import type { RuntimeHealthSummary } from "../../api";
import {
  formatDateTime,
  formatRuntimeApiError,
  isPermissionDeniedError,
  runtimeStatusColor,
} from "../../utils";

interface RuntimeHealthPanelProps {
  data: RuntimeHealthSummary | undefined;
  error: unknown;
  isLoading: boolean;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function RuntimeHealthPanel({
  data,
  error,
  isLoading,
  isRefreshing,
  onRefresh,
}: RuntimeHealthPanelProps) {
  if (isLoading) {
    return (
      <section className="rounded-xl border border-hairline bg-canvas p-5">
        <p className="m-0 text-sm text-muted">正在读取 Runtime health...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border border-danger/20 bg-danger/6 p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="m-0 text-sm font-semibold text-danger">
              {isPermissionDeniedError(error)
                ? "权限不足，无法读取 Runtime health。"
                : "Runtime health 读取失败"}
            </p>
            <p className="m-0 mt-1 text-sm text-muted-strong">{formatRuntimeApiError(error)}</p>
          </div>
          <Button size="sm" type="button" variant="outline" onPress={onRefresh}>
            重新读取
          </Button>
        </div>
      </section>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <section className="rounded-xl border border-hairline bg-canvas p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="m-0 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
            Runtime Health
          </p>
          <h2 className="m-0 mt-1 text-[22px] font-semibold tracking-[-0.03em] text-ink">
            运行健康摘要
          </h2>
          <p className="m-0 mt-1 text-sm text-muted">
            生成时间：{formatDateTime(data.generated_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Chip color={runtimeStatusColor(data.partial_status)} size="sm" variant="soft">
            partial: {data.partial_status}
          </Chip>
          <Chip color={runtimeStatusColor(data.websocket_status_hint)} size="sm" variant="soft">
            realtime: {data.websocket_status_hint}
          </Chip>
          <Button
            isDisabled={isRefreshing}
            size="sm"
            type="button"
            variant="outline"
            onPress={onRefresh}
          >
            {isRefreshing ? "刷新中..." : "刷新快照"}
          </Button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <HealthStat label="运行中 AgentRun" value={data.active_agent_run_count} />
        <HealthStat label="近期失败 AgentRun" value={data.recent_failed_agent_run_count} />
        <HealthStat label="工具失败" value={data.recent_failed_tool_invocation_count} />
        <HealthStat label="Critical errors" value={data.runtime_error_severity_summary.critical} />
        <HealthStat label="Warning errors" value={data.runtime_error_severity_summary.warning} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Chip color={runtimeStatusColor(data.backend_status.api)} size="sm" variant="soft">
          API {data.backend_status.api}
        </Chip>
        <Chip color={runtimeStatusColor(data.backend_status.scheduler)} size="sm" variant="soft">
          Scheduler {data.backend_status.scheduler}
        </Chip>
        <Chip color={runtimeStatusColor(data.backend_status.worker)} size="sm" variant="soft">
          Worker {data.backend_status.worker}
        </Chip>
      </div>

      {data.unavailable_resources.length > 0 ? (
        <div className="mt-4 rounded-lg border border-warning/25 bg-warning/8 px-4 py-3">
          <p className="m-0 text-sm font-semibold text-warning">局部资源降级</p>
          <ul className="m-0 mt-2 grid list-none gap-1 p-0 text-sm text-muted-strong">
            {data.unavailable_resources.map((resource) => (
              <li key={resource.reason}>{resource.message}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function HealthStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-3">
      <span className="block text-xs font-medium text-muted">{label}</span>
      <span className="mt-1 block text-[24px] font-semibold tracking-[-0.04em] text-ink">
        {value}
      </span>
    </div>
  );
}

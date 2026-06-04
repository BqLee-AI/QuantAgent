import { Card, Chip } from "@heroui/react";

import {
  usePluginAuditViewQuery,
  usePluginDependenciesViewQuery,
  usePluginDetailQuery,
  usePluginHealthViewQuery,
} from "../../queries/use-plugin-detail";
import type { PluginDetailResponse } from "../../api/plugin-detail.contracts";
import {
  formatApiError,
  formatAvailability,
  formatConfigState,
  formatOptional,
  formatPluginDescription,
  formatPluginStatus,
  formatPluginType,
} from "../../utils/plugin-detail-format";
import {
  PluginDetailEmptyState,
  PluginDetailErrorState,
  PluginDetailLoadingState,
} from "../states/plugin-detail-state";
import { PluginDetailWorkspace } from "./plugin-detail-workspace";

export function PluginDetailPage({ pluginId }: { pluginId: string }) {
  const detailQuery = usePluginDetailQuery(pluginId);
  const dependenciesQuery = usePluginDependenciesViewQuery(pluginId);
  const healthQuery = usePluginHealthViewQuery(pluginId);
  const auditQuery = usePluginAuditViewQuery(pluginId);

  if (detailQuery.isLoading) {
    return <PluginDetailLoadingState />;
  }

  if (detailQuery.isError) {
    return <PluginDetailErrorState message={formatApiError(detailQuery.error)} />;
  }

  if (!detailQuery.data) {
    return <PluginDetailEmptyState pluginId={pluginId} />;
  }

  const detail = detailQuery.data;

  return (
    <div className="grid gap-5">
      <section className="page-header">
        <div className="min-w-0">
          <h1 className="page-title font-extrabold">{detail.overview.name}</h1>
          <p className="page-description">
            {formatPluginDescription(detail.overview.plugin_id, detail.overview.description)}
          </p>
        </div>
      </section>

      <PluginDetailHero detail={detail} />

      <PluginDetailWorkspace
        auditError={auditQuery.isError ? auditQuery.error : undefined}
        auditView={auditQuery.data}
        dependenciesError={dependenciesQuery.isError ? dependenciesQuery.error : undefined}
        dependenciesView={dependenciesQuery.data}
        detail={detail}
        healthError={healthQuery.isError ? healthQuery.error : undefined}
        healthView={healthQuery.data}
      />
    </div>
  );
}

function PluginDetailHero({ detail }: { detail: PluginDetailResponse }) {
  const { overview } = detail;

  return (
    <Card className="border border-hairline bg-surface shadow-sm">
      <Card.Content className="grid gap-4 p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="default" size="sm" variant="soft">
                {formatPluginType(overview.type)}
              </Chip>
              <Chip color={pluginStatusColor(overview.status)} size="sm" variant="soft">
                {formatPluginStatus(overview.status)}
              </Chip>
              <Chip color="default" size="sm" variant="soft">
                {overview.source}
              </Chip>
              {overview.active_config_state !== "valid" ? (
                <Chip color="warning" size="sm" variant="soft">
                  配置：{formatConfigState(overview.active_config_state)}
                </Chip>
              ) : null}
            </div>
            <p className="m-0 mt-3 break-all text-body-sm text-muted">{overview.plugin_id}</p>
          </div>
          <div className="grid gap-2 text-body-sm sm:grid-cols-3 xl:min-w-[32rem]">
            <HeroMetric label="安装版本" value={formatOptional(overview.installed_version)} />
            <HeroMetric label="依赖状态" value={formatAvailability(detail.dependency_summary.availability)} />
            <HeroMetric label="健康状态" value={formatAvailability(detail.health_summary.availability)} />
          </div>
        </div>
      </Card.Content>
    </Card>
  );
}

function HeroMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
      <p className="m-0 text-[11px] font-semibold text-muted">{label}</p>
      <p className="m-0 mt-1 truncate text-body-sm font-bold text-ink">{value}</p>
    </div>
  );
}

function pluginStatusColor(status: string) {
  if (status === "failed" || status === "invalid") {
    return "danger";
  }
  if (status === "enabled" || status === "valid" || status === "started") {
    return "success";
  }
  if (status === "disabled" || status === "stopped" || status === "discovered") {
    return "warning";
  }
  return "default";
}

import { Chip } from "@heroui/react";

import type {
  PluginAuditViewResponse,
  PluginDependenciesViewResponse,
  PluginDetailResponse,
  PluginHealthViewResponse,
} from "../../api/plugin-detail.contracts";
import {
  formatAvailability,
  formatConfigState,
  formatDateTime,
  formatErrorSummary,
  formatHealthStatus,
  formatKeyLabel,
  formatOptional,
} from "../../utils/plugin-detail-format";
import { DetailSectionCard } from "./detail-section-card";
import { KeyValueGrid } from "./key-value-grid";

export function PluginConfigDependencySection({
  dependenciesError,
  dependenciesView,
  detail,
}: {
  dependenciesError?: unknown;
  dependenciesView?: PluginDependenciesViewResponse;
  detail: PluginDetailResponse;
}) {
  return (
    <DetailSectionCard
      title="依赖状态"
    >
      <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          <Chip
            color={detail.dependency_summary.availability.state === "ready" ? "success" : "warning"}
            size="sm"
            variant="soft"
          >
            依赖：{formatAvailability(detail.dependency_summary.availability)}
          </Chip>
          {detail.config_summary.config_state !== "valid" ? (
            <Chip color="warning" size="sm" variant="soft">
              配置：{formatConfigState(detail.config_summary.config_state)}
            </Chip>
          ) : null}
        </div>
        <KeyValueGrid
          rows={[
            {
              label: formatKeyLabel("missing_dependencies"),
              value: String(detail.dependency_summary.missing_count),
            },
            {
              label: "插件依赖",
              value: dependenciesView ? String(dependenciesView.plugin_dependencies.length) : "-",
            },
            {
              label: "Python 依赖",
              value: dependenciesView ? String(dependenciesView.python_dependencies.length) : "-",
            },
            {
              label: formatKeyLabel("dependency_blocker"),
              value: formatOptional(detail.dependency_summary.blocked_reason_summary),
            },
          ]}
        />
        {dependenciesError ? (
          <p className="m-0 rounded-lg border border-warning/30 bg-warning/10 px-3 py-3 text-body-sm text-warning">
            依赖详情加载失败：{formatOptional((dependenciesError as Error)?.message)}
          </p>
        ) : null}
      </div>
    </DetailSectionCard>
  );
}

export function PluginHealthAuditOpsSection({
  auditError,
  auditView,
  detail,
  healthError,
  healthView,
}: {
  auditError?: unknown;
  auditView?: PluginAuditViewResponse;
  detail: PluginDetailResponse;
  healthError?: unknown;
  healthView?: PluginHealthViewResponse;
}) {
  return (
    <DetailSectionCard
      title="健康状态"
    >
      <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          <Chip
            color={detail.health_summary.status === "healthy" ? "success" : "warning"}
            size="sm"
            variant="soft"
          >
            状态：{formatHealthStatus(detail.health_summary.status)}
          </Chip>
          <Chip
            color={detail.health_summary.availability.state === "ready" ? "success" : "default"}
            size="sm"
            variant="soft"
          >
            健康视图：{healthView ? formatAvailability(healthView.availability) : healthError ? "加载失败" : "加载中"}
          </Chip>
        </div>
        <KeyValueGrid
          rows={[
            {
              label: formatKeyLabel("health"),
              value: formatAvailability(detail.health_summary.availability),
            },
            { label: formatKeyLabel("last_check_at"), value: formatDateTime(detail.health_summary.last_check_at) },
            {
              label: formatKeyLabel("runtime_errors"),
              value: String(healthView?.recent_runtime_error_count ?? detail.health_summary.recent_runtime_error_count),
            },
            {
              label: formatKeyLabel("health_error"),
              value: formatErrorSummary(detail.health_summary.last_error_summary),
            },
            {
              label: "审计视图",
              value: auditView ? formatAvailability(auditView.availability) : auditError ? "加载失败" : "加载中",
            },
            { label: "审计记录", value: String(auditView?.entries.length ?? 0) },
          ]}
        />
        {detail.health_summary.last_error_summary ? (
          <p className="m-0 rounded-lg border border-warning/30 bg-warning/10 px-3 py-3 text-body-sm text-warning">
            最近错误：{formatErrorSummary(detail.health_summary.last_error_summary)}
          </p>
        ) : null}
      </div>
    </DetailSectionCard>
  );
}

import { Card, Chip } from "@heroui/react";

import type { PluginRecordResponse } from "../../../api/contracts";
import { LinkButton } from "@/shared/ui";
import {
  formatErrorSummary,
  formatOptional,
  formatPluginDescription,
  formatPluginStatus,
  formatPluginType,
} from "../../utils/plugin-detail-format";

type PluginListCardProps = {
  plugin: PluginRecordResponse;
};

export function PluginListCard({ plugin }: PluginListCardProps) {
  const manifest = plugin.manifest;
  const name = manifest?.name ?? plugin.id;
  const type = manifest?.type ?? "unknown";
  const version = formatOptional(manifest?.version);
  const capabilityCount = manifest?.capabilities?.length ?? 0;
  const sourceBindingCount = manifest?.source_bindings?.length ?? 0;
  const hasError = Boolean(plugin.last_error);

  return (
    <Card
      className={[
        "border bg-surface shadow-sm transition-colors",
        hasError ? "border-warning/40" : "border-hairline hover:border-primary/50",
      ].join(" ")}
    >
      <Card.Content className="grid gap-1.5 p-2.5">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="m-0 truncate text-title-sm font-bold text-ink">{name}</h2>
              <Chip color={statusColor(plugin.status)} size="sm" variant="soft">
                {formatPluginStatus(plugin.status)}
              </Chip>
            </div>
            <p className="m-0 mt-1 truncate text-body-sm text-muted">{plugin.id}</p>
          </div>
          <Chip color="default" size="sm" variant="soft">
            {formatPluginType(type)}
          </Chip>
        </div>

        <p className="m-0 line-clamp-1 text-body-sm leading-5 text-muted">
          {formatPluginDescription(plugin.id, manifest?.description)}
        </p>

        <div className="grid gap-x-3 gap-y-1 text-body-sm text-muted sm:grid-cols-2">
          <MetaItem label="版本" value={version} />
          <MetaItem label="来源" value={plugin.source} />
          <MetaItem label="能力" value={`${capabilityCount} 项`} />
          <MetaItem label="绑定模板" value={`${sourceBindingCount} 项`} />
        </div>

        <div className="rounded-md border border-hairline bg-surface-soft px-2.5 py-1">
          <p className="m-0 line-clamp-1 text-body-sm text-muted">
            最近错误：
            <span className={hasError ? "text-warning" : "text-muted"}>
              {formatErrorSummary(plugin.last_error)}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-hairline pt-1">
          <div className="flex flex-wrap gap-1.5">
            {manifest?.permissions?.length ? (
              <Chip color="warning" size="sm" variant="soft">
                权限 {manifest.permissions.length} 项
              </Chip>
            ) : null}
          </div>
          <LinkButton
            className="gap-1 px-2 text-primary hover:bg-primary/8"
            params={{ pluginId: plugin.id }}
            to="/plugins/$pluginId"
            variant="ghost"
          >
            查看
          </LinkButton>
        </div>
      </Card.Content>
    </Card>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <p className="m-0 min-w-0 truncate">
      <span className="text-muted">{label}: </span>
      <span className="font-semibold text-ink">{value}</span>
    </p>
  );
}

function statusColor(status: string) {
  if (status === "failed" || status === "invalid") {
    return "danger";
  }
  if (status === "enabled" || status === "valid") {
    return "success";
  }
  if (status === "disabled" || status === "discovered") {
    return "warning";
  }
  return "default";
}

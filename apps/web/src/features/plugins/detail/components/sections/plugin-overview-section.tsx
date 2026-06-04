import { Chip } from "@heroui/react";

import type { PluginDetailResponse } from "../../api/plugin-detail.contracts";
import {
  formatAvailability,
  formatConfigState,
  formatErrorSummary,
  formatKeyLabel,
  formatOptional,
  formatPluginStatus,
  formatPluginType,
} from "../../utils/plugin-detail-format";
import { DetailSectionCard } from "./detail-section-card";
import { KeyValueGrid } from "./key-value-grid";

export function PluginOverviewSection({ detail }: { detail: PluginDetailResponse }) {
  const { overview } = detail;

  return (
    <DetailSectionCard
      title="插件治理摘要"
    >
      <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          <Chip size="sm" variant="soft">
            {formatPluginType(overview.type)}
          </Chip>
          <Chip size="sm" variant="soft">
            {formatPluginStatus(overview.status)}
          </Chip>
          <Chip size="sm" variant="soft">
            {overview.source}
          </Chip>
          {overview.active_config_state !== "valid" ? (
            <Chip color="warning" size="sm" variant="soft">
              配置：{formatConfigState(overview.active_config_state)}
            </Chip>
          ) : null}
        </div>
        <KeyValueGrid
          rows={[
            { label: formatKeyLabel("plugin_id"), value: overview.plugin_id },
            { label: formatKeyLabel("installed_version"), value: formatOptional(overview.installed_version) },
            { label: formatKeyLabel("active_version"), value: formatOptional(overview.active_version) },
            { label: formatKeyLabel("blocked_reason"), value: formatOptional(overview.blocked_reason) },
            { label: formatKeyLabel("last_error"), value: formatErrorSummary(overview.last_error_summary) },
            { label: formatKeyLabel("ops_state"), value: formatAvailability(detail.ops_summary.availability) },
          ]}
        />
      </div>
    </DetailSectionCard>
  );
}

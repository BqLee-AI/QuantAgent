import { Chip, Table } from "@heroui/react";

import { DetailSectionCard } from "../../detail/components/sections/detail-section-card";
import { formatApiError } from "../../detail/utils/plugin-detail-format";
import type { PluginOverview } from "../../detail/api/plugin-detail.contracts";
import { useSourceBindingsQuery } from "../queries/use-source-bindings";
import { summarizeBindingActivity, summarizeBindingScope } from "../utils/source-binding-format";

const bindingStatusMeta: Record<string, { color: "default" | "success" | "warning"; label: string }> = {
  active: { color: "success", label: "运行中" },
  disabled: { color: "default", label: "已禁用" },
  paused: { color: "warning", label: "已暂停" },
};

export function SourceBindingsPanel({ overview }: { overview: PluginOverview }) {
  const isIndustryPlugin = overview.type === "industry";
  const bindingsQuery = useSourceBindingsQuery(
    {
      limit: 50,
      ownerId: overview.plugin_id,
      ownerType: "industry",
    },
    isIndustryPlugin,
  );

  if (!isIndustryPlugin) {
    return (
      <DetailSectionCard
        title="仅 Industry 插件展示内嵌绑定管理面"
      >
        <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-4 text-body-sm text-muted">
          当前插件类型为 {overview.type}，SourceBinding 管理面不适用。
        </p>
      </DetailSectionCard>
    );
  }

  if (bindingsQuery.isError) {
    return (
      <DetailSectionCard
        title="绑定关系暂不可用"
      >
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-4 text-body-sm text-warning">
          {formatApiError(bindingsQuery.error)}
        </div>
      </DetailSectionCard>
    );
  }

  const bindings = bindingsQuery.data?.items ?? [];

  return (
    <DetailSectionCard
      title="Industry 内嵌 SourceBinding 管理面"
    >
      {bindingsQuery.isLoading ? (
        <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-4 text-body-sm text-muted">
          正在加载 SourceBinding...
        </p>
      ) : null}

      {!bindingsQuery.isLoading && bindings.length === 0 ? (
        <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-4 text-body-sm text-muted">
          暂无 SourceBinding 记录。若 manifest 只声明 template 但尚未持久化绑定，这里保持空状态。
        </p>
      ) : null}

      {bindings.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <Table aria-label="SourceBinding 列表" variant="secondary">
            <Table.Content className="min-w-[64rem]">
              <Table.Header>
                <Table.Column>绑定 ID</Table.Column>
                <Table.Column>Source 插件</Table.Column>
                <Table.Column>状态</Table.Column>
                <Table.Column>范围 / 健康</Table.Column>
                <Table.Column>最近活动</Table.Column>
                <Table.Column>允许动作</Table.Column>
              </Table.Header>
              <Table.Body items={bindings}>
                {(binding) => (
                  <Table.Row key={binding.id}>
                    <Table.Cell>{binding.id}</Table.Cell>
                    <Table.Cell>{binding.source_plugin_id}</Table.Cell>
                    <Table.Cell>
                      <Chip
                        color={formatBindingStatus(binding.status).color}
                        size="sm"
                        variant="soft"
                      >
                        {formatBindingStatus(binding.status).label}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>{summarizeBindingScope(binding)}</Table.Cell>
                    <Table.Cell>{summarizeBindingActivity(binding)}</Table.Cell>
                    <Table.Cell>{(binding.allowed_actions ?? []).map(formatBindingAction).join(", ") || "-"}</Table.Cell>
                  </Table.Row>
                )}
              </Table.Body>
            </Table.Content>
          </Table>
        </div>
      ) : null}
    </DetailSectionCard>
  );
}

function formatBindingStatus(status: string) {
  return bindingStatusMeta[status] ?? { color: "default", label: status };
}

function formatBindingAction(action: string) {
  if (action === "pause") {
    return "暂停";
  }
  if (action === "resume") {
    return "恢复";
  }
  if (action === "run-now") {
    return "立即运行";
  }
  return action;
}

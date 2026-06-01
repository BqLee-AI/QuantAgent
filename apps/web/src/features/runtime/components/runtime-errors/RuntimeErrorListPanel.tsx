import { Chip, Table } from "@heroui/react";

import type { RuntimeErrorSummary, RuntimeListResponse } from "../../api";
import {
  formatDateTime,
  getListUnavailableMessage,
  runtimeSeverityColor,
  runtimeStatusColor,
} from "../../utils";
import { RuntimeSection } from "../shared/RuntimeSection";
import { RuntimePanelState } from "../states/RuntimePanelState";

interface RuntimeErrorListPanelProps {
  data: RuntimeListResponse<RuntimeErrorSummary> | undefined;
  error: unknown;
  isLoading: boolean;
  onRetry: () => void;
}

export function RuntimeErrorListPanel({
  data,
  error,
  isLoading,
  onRetry,
}: RuntimeErrorListPanelProps) {
  const unavailableLabel = getListUnavailableMessage(data);
  const items = [...(data?.items ?? [])].sort(
    (left, right) => severityRank(right.severity) - severityRank(left.severity),
  );

  return (
    <RuntimeSection
      description="严重 runtime error 置顶展示，错误信息必须来自后端脱敏摘要。"
      title="Runtime Errors"
    >
      {isLoading || error || unavailableLabel || items.length === 0 ? (
        <RuntimePanelState
          emptyLabel="暂无 RuntimeError。"
          error={error}
          isLoading={isLoading}
          unavailableLabel={unavailableLabel}
          onRetry={onRetry}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <Table aria-label="RuntimeError 列表" variant="secondary">
            <Table.Content className="min-w-[70rem]">
              <Table.Header>
                <Table.Column>component</Table.Column>
                <Table.Column>severity</Table.Column>
                <Table.Column>状态</Table.Column>
                <Table.Column>error_code</Table.Column>
                <Table.Column>message</Table.Column>
                <Table.Column>provider</Table.Column>
                <Table.Column>trace / event / plugin</Table.Column>
                <Table.Column>created_at</Table.Column>
              </Table.Header>
              <Table.Body items={items}>
                {(item) => (
                  <Table.Row key={item.error_id}>
                    <Table.Cell>{item.component}</Table.Cell>
                    <Table.Cell>
                      <Chip color={runtimeSeverityColor(item.severity)} size="sm" variant="soft">
                        {item.severity}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>
                      <Chip color={runtimeStatusColor(item.status)} size="sm" variant="soft">
                        {item.status}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>{item.error_code}</Table.Cell>
                    <Table.Cell>{item.error_message_summary}</Table.Cell>
                    <Table.Cell>{item.provider ?? item.provider_policy ?? "-"}</Table.Cell>
                    <Table.Cell>
                      {item.trace_id ?? item.event_id ?? item.plugin_id ?? "-"}
                    </Table.Cell>
                    <Table.Cell>{formatDateTime(item.created_at)}</Table.Cell>
                  </Table.Row>
                )}
              </Table.Body>
            </Table.Content>
          </Table>
        </div>
      )}
    </RuntimeSection>
  );
}

function severityRank(value: string): number {
  switch (value.toLowerCase()) {
    case "critical":
      return 3;
    case "warning":
      return 2;
    case "info":
      return 1;
    default:
      return 0;
  }
}

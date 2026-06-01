import { Chip, Table } from "@heroui/react";

import type { RuntimeListResponse, SchedulerRunSummary } from "../../api";
import {
  formatDateTime,
  formatDuration,
  formatErrorSummary,
  getListUnavailableMessage,
  runtimeStatusColor,
} from "../../utils";
import { RuntimeSection } from "../shared/RuntimeSection";
import { RuntimePanelState } from "../states/RuntimePanelState";

interface SchedulerRunListPanelProps {
  data: RuntimeListResponse<SchedulerRunSummary> | undefined;
  error: unknown;
  isLoading: boolean;
  onRetry: () => void;
}

export function SchedulerRunListPanel({
  data,
  error,
  isLoading,
  onRetry,
}: SchedulerRunListPanelProps) {
  const unavailableLabel = getListUnavailableMessage(data);
  const items = data?.items ?? [];

  return (
    <RuntimeSection
      description="scheduler run V1 仅观察最近运行与失败摘要，不提供触发、重跑或暂停控制。"
      title="Scheduler Runs"
    >
      {isLoading || error || unavailableLabel || items.length === 0 ? (
        <RuntimePanelState
          emptyLabel="暂无 SchedulerRun。"
          error={error}
          isLoading={isLoading}
          unavailableLabel={unavailableLabel}
          onRetry={onRetry}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <Table aria-label="SchedulerRun 列表" variant="secondary">
            <Table.Content className="min-w-[58rem]">
              <Table.Header>
                <Table.Column>run_id</Table.Column>
                <Table.Column>binding / plugin</Table.Column>
                <Table.Column>trigger</Table.Column>
                <Table.Column>状态</Table.Column>
                <Table.Column>时间</Table.Column>
                <Table.Column>request_id</Table.Column>
                <Table.Column>错误摘要</Table.Column>
              </Table.Header>
              <Table.Body items={items}>
                {(item) => (
                  <Table.Row key={item.run_id}>
                    <Table.Cell>{item.run_id}</Table.Cell>
                    <Table.Cell>
                      {item.binding_id ?? "-"}
                      <br />
                      {item.plugin_id ?? "-"}
                    </Table.Cell>
                    <Table.Cell>{item.trigger_type}</Table.Cell>
                    <Table.Cell>
                      <Chip color={runtimeStatusColor(item.status)} size="sm" variant="soft">
                        {item.status}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>
                      {formatDateTime(item.started_at)}
                      <br />
                      {formatDuration(item.duration_ms)}
                    </Table.Cell>
                    <Table.Cell>{item.request_id ?? "-"}</Table.Cell>
                    <Table.Cell>{formatErrorSummary(item.error_summary)}</Table.Cell>
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

import { Chip, Table } from "@heroui/react";

import { LinkButton } from "@/shared/ui";

import type { RuntimeListResponse, ToolInvocationSummary } from "../../api";
import {
  formatDuration,
  formatErrorSummary,
  getListUnavailableMessage,
  runtimeStatusColor,
} from "../../utils";
import { RuntimeSection } from "../shared/RuntimeSection";
import { RuntimePanelState } from "../states/RuntimePanelState";

interface ToolInvocationListPanelProps {
  data: RuntimeListResponse<ToolInvocationSummary> | undefined;
  error: unknown;
  isLoading: boolean;
  onRetry: () => void;
}

export function ToolInvocationListPanel({
  data,
  error,
  isLoading,
  onRetry,
}: ToolInvocationListPanelProps) {
  const unavailableLabel = getListUnavailableMessage(data);
  const items = data?.items ?? [];

  return (
    <RuntimeSection
      description="工具调用只展示脱敏摘要、风险等级、重试次数和 trace 关联。"
      title="Tool Invocations"
    >
      {isLoading || error || unavailableLabel || items.length === 0 ? (
        <RuntimePanelState
          emptyLabel="暂无 ToolInvocation。"
          error={error}
          isLoading={isLoading}
          unavailableLabel={unavailableLabel}
          onRetry={onRetry}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <Table aria-label="ToolInvocation 列表" variant="secondary">
            <Table.Content className="min-w-[72rem]">
              <Table.Header>
                <Table.Column>invocation_id</Table.Column>
                <Table.Column>tool / plugin</Table.Column>
                <Table.Column>risk</Table.Column>
                <Table.Column>状态</Table.Column>
                <Table.Column>关联</Table.Column>
                <Table.Column>耗时 / 重试</Table.Column>
                <Table.Column>错误摘要</Table.Column>
                <Table.Column>入口</Table.Column>
              </Table.Header>
              <Table.Body items={items}>
                {(item) => (
                  <Table.Row key={item.invocation_id}>
                    <Table.Cell>{item.invocation_id}</Table.Cell>
                    <Table.Cell>
                      {item.tool_id}
                      <br />
                      {item.plugin_id ?? "-"}
                    </Table.Cell>
                    <Table.Cell>{item.risk_level ?? "-"}</Table.Cell>
                    <Table.Cell>
                      <Chip color={runtimeStatusColor(item.status)} size="sm" variant="soft">
                        {item.status}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>
                      {item.agent_run_id ?? item.event_id ?? item.trace_id ?? "-"}
                    </Table.Cell>
                    <Table.Cell>
                      {formatDuration(item.duration_ms)}
                      <br />
                      retry {item.retry_count}
                    </Table.Cell>
                    <Table.Cell>{formatErrorSummary(item.error_summary)}</Table.Cell>
                    <Table.Cell>
                      <LinkButton
                        to="/runtime/tools/$invocationId"
                        params={{ invocationId: item.invocation_id }}
                        variant="outline"
                      >
                        详情
                      </LinkButton>
                    </Table.Cell>
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

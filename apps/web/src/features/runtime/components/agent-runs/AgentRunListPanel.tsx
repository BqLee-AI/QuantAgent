import { Chip, Table } from "@heroui/react";

import { LinkButton } from "@/shared/ui";

import type { AgentRunSummary, RuntimeListResponse } from "../../api";
import {
  formatDateTime,
  formatDuration,
  formatErrorSummary,
  formatObjectSummary,
  getListUnavailableMessage,
  runtimeStatusColor,
} from "../../utils";
import { RuntimePanelState } from "../states/RuntimePanelState";
import { RuntimeSection } from "../shared/RuntimeSection";

interface AgentRunListPanelProps {
  data: RuntimeListResponse<AgentRunSummary> | undefined;
  error: unknown;
  isLoading: boolean;
  onRetry: () => void;
}

export function AgentRunListPanel({ data, error, isLoading, onRetry }: AgentRunListPanelProps) {
  const unavailableLabel = getListUnavailableMessage(data);
  const items = data?.items ?? [];

  return (
    <RuntimeSection
      description="结构化运行摘要，不展示 raw prompt 或完整推理链。"
      title="Agent Runs"
    >
      {isLoading || error || unavailableLabel || items.length === 0 ? (
        <RuntimePanelState
          emptyLabel="暂无 AgentRun。"
          error={error}
          isLoading={isLoading}
          unavailableLabel={unavailableLabel}
          onRetry={onRetry}
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <Table aria-label="AgentRun 列表" variant="secondary">
            <Table.Content className="min-w-[78rem]">
              <Table.Header>
                <Table.Column>run_id</Table.Column>
                <Table.Column>event / trace</Table.Column>
                <Table.Column>类型</Table.Column>
                <Table.Column>状态</Table.Column>
                <Table.Column>模型</Table.Column>
                <Table.Column>Token / Cost</Table.Column>
                <Table.Column>时间</Table.Column>
                <Table.Column>错误摘要</Table.Column>
                <Table.Column>入口</Table.Column>
              </Table.Header>
              <Table.Body items={items}>
                {(item) => (
                  <Table.Row key={item.run_id}>
                    <Table.Cell>{item.run_id}</Table.Cell>
                    <Table.Cell>{item.event_id ?? item.trace_id ?? "-"}</Table.Cell>
                    <Table.Cell>{item.run_type}</Table.Cell>
                    <Table.Cell>
                      <Chip color={runtimeStatusColor(item.status)} size="sm" variant="soft">
                        {item.status}
                      </Chip>
                    </Table.Cell>
                    <Table.Cell>{item.model_used ?? item.provider_policy ?? "-"}</Table.Cell>
                    <Table.Cell>
                      {formatObjectSummary(item.token_usage_summary)}
                      <br />
                      {formatObjectSummary(item.cost_estimate_summary)}
                    </Table.Cell>
                    <Table.Cell>
                      {formatDateTime(item.started_at)}
                      <br />
                      {formatDuration(item.duration_ms)}
                    </Table.Cell>
                    <Table.Cell>{formatErrorSummary(item.error_summary)}</Table.Cell>
                    <Table.Cell>
                      <LinkButton
                        to="/runtime/agents/$runId"
                        params={{ runId: item.run_id }}
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

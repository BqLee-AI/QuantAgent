import {
  Chip,
  Table,
} from '@heroui/react';

import type { ModelInvocation } from '../../api';

interface ModelInvocationTableProps {
  invocations: readonly ModelInvocation[];
  isError: boolean;
  isLoading: boolean;
}

export function ModelInvocationTable({
  invocations,
  isError,
  isLoading,
}: ModelInvocationTableProps) {
  if (isError) {
    return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">模型调用记录加载失败。</p>;
  }

  if (invocations.length === 0) {
    return (
      <p className="rounded-md border border-hairline bg-surface-soft px-3 py-4 text-sm text-muted">
        {isLoading ? '加载模型调用记录...' : '暂无模型调用记录。'}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-hairline">
      <Table aria-label="模型调用记录" variant="secondary">
        <Table.Content className="min-w-[52rem]">
          <Table.Header>
            <Table.Column>时间</Table.Column>
            <Table.Column>供应商</Table.Column>
            <Table.Column>模型</Table.Column>
            <Table.Column>状态</Table.Column>
            <Table.Column>Prompt tokens</Table.Column>
            <Table.Column>Completion tokens</Table.Column>
            <Table.Column>Total tokens</Table.Column>
            <Table.Column>请求 ID</Table.Column>
          </Table.Header>
          <Table.Body items={invocations}>
            {(item) => (
              <Table.Row key={`${item.id ?? item.created_at}-${item.request_id ?? 'none'}`}>
                <Table.Cell>{new Date(item.created_at).toLocaleString()}</Table.Cell>
                <Table.Cell>{item.provider_name}</Table.Cell>
                <Table.Cell>{item.model || '-'}</Table.Cell>
                <Table.Cell>
                  <Chip color={item.status === 'succeeded' ? 'success' : 'danger'} size="sm" variant="soft">
                    {item.status}
                  </Chip>
                </Table.Cell>
                <Table.Cell>{item.token_usage.prompt_tokens ?? '-'}</Table.Cell>
                <Table.Cell>{item.token_usage.completion_tokens ?? '-'}</Table.Cell>
                <Table.Cell>{item.token_usage.total_tokens ?? '-'}</Table.Cell>
                <Table.Cell>{item.request_id ?? '-'}</Table.Cell>
              </Table.Row>
            )}
          </Table.Body>
        </Table.Content>
      </Table>
    </div>
  );
}

import { Chip } from '@heroui/react';

import type { AgentRunChatMessage } from '../../types';
import { AgentRunArtifactCard } from '../events/AgentRunArtifactCard';
import { AgentRunSubagentCard } from '../events/AgentRunSubagentCard';
import { AgentRunToolCard } from '../events/AgentRunToolCard';

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function AgentRunMessageBubble({ message }: { message: AgentRunChatMessage }) {
  if (message.kind === 'tool') return <AgentRunToolCard message={message} />;
  if (message.kind === 'subagent') return <AgentRunSubagentCard message={message} />;
  if (message.kind === 'artifact') return <AgentRunArtifactCard message={message} />;

  if (message.kind === 'todo') {
    return (
      <div className="rounded-lg border border-hairline bg-surface-card px-3 py-2">
        <div className="flex items-center gap-2">
          <Chip size="sm" variant="soft">todo</Chip>
          <span className="text-[12px] text-muted">{formatTime(message.createdAt)}</span>
        </div>
        <ul className="mt-2 grid gap-1.5 text-[13px] text-muted-strong">
          {message.todos.map((todo) => (
            <li key={`${todo.status}-${todo.content}`} className="flex gap-2">
              <span className="font-semibold text-ink">{todo.status}</span>
              <span>{todo.content}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const isError = message.kind === 'error';
  const title = message.kind === 'final' ? message.title : message.kind === 'assistant' ? message.title : '运行事件';

  return (
    <div className={isError ? 'rounded-xl border border-trading-down/30 bg-trading-down/5 px-4 py-3' : 'rounded-xl border border-hairline bg-canvas px-4 py-3'}>
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          {message.kind}
        </Chip>
        <h3 className="m-0 text-[14px] font-semibold text-ink">{title}</h3>
        <span className="text-[12px] text-muted">{formatTime(message.createdAt)}</span>
      </div>
      <p className={isError ? 'mt-2 text-[13px] text-trading-down' : 'mt-2 text-[13px] text-muted-strong'}>
        {message.summary}
      </p>
      {message.kind === 'final' && message.tradeDecision ? (
        <p className="mt-2 rounded-lg bg-surface-soft px-3 py-2 text-[12px] font-semibold text-ink">
          trade_decision: {message.tradeDecision}
        </p>
      ) : null}
    </div>
  );
}

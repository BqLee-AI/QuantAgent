import { Chip } from '@heroui/react';

import type { AgentRunChatState } from '../../types';

const statusLabels: Record<AgentRunChatState['status'], string> = {
  aborted: '已停止',
  completed: '已完成',
  failed: '失败',
  idle: '未运行',
  streaming: '运行中',
};

const statusTone: Record<AgentRunChatState['status'], string> = {
  aborted: 'bg-surface-soft text-muted-strong',
  completed: 'bg-trading-up/10 text-trading-up',
  failed: 'bg-trading-down/10 text-trading-down',
  idle: 'bg-surface-soft text-muted-strong',
  streaming: 'bg-primary/10 text-primary',
};

export function AgentRunStatusBar({ state }: { state: AgentRunChatState }) {
  return (
    <section className="flex flex-wrap items-center gap-2 rounded-xl border border-hairline bg-surface-card px-4 py-2.5 text-[12px] text-muted-strong">
      <Chip className={statusTone[state.status]} size="sm" variant="soft">
        {statusLabels[state.status]}
      </Chip>
      <span>Scenario: {state.currentScenario}</span>
      {state.agentRunId ? <span>Run: {state.agentRunId}</span> : null}
      {state.lastTraceId ? <span>Trace: {state.lastTraceId}</span> : null}
      {state.errorSummary ? <span className="text-trading-down">{state.errorSummary}</span> : null}
    </section>
  );
}

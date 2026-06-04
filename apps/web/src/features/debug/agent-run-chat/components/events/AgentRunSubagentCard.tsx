import { Chip } from '@heroui/react';

import type { AgentRunSubagentMessage } from '../../types';

export function AgentRunSubagentCard({ message }: { message: AgentRunSubagentMessage }) {
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          subagent.{message.status}
        </Chip>
        <span className="text-[13px] font-semibold text-ink">{message.subagentName}</span>
      </div>
      {message.subagentId ? <p className="mt-1 text-[12px] text-muted">ID: {message.subagentId}</p> : null}
      <p className="mt-2 text-[13px] text-muted-strong">{message.summary}</p>
    </div>
  );
}

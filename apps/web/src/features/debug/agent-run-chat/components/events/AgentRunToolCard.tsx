import { Chip } from '@heroui/react';

import type { AgentRunToolMessage } from '../../types';

export function AgentRunToolCard({ message }: { message: AgentRunToolMessage }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface-card px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          tool.{message.status}
        </Chip>
        <span className="text-[13px] font-semibold text-ink">{message.toolName}</span>
      </div>
      <p className="mt-2 text-[13px] text-muted-strong">{message.summary}</p>
    </div>
  );
}

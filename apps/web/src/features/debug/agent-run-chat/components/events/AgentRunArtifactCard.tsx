import { Chip } from '@heroui/react';

import type { AgentRunArtifactMessage } from '../../types';

export function AgentRunArtifactCard({ message }: { message: AgentRunArtifactMessage }) {
  return (
    <div className="rounded-lg border border-hairline bg-canvas px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          artifact
        </Chip>
        <span className="text-[13px] font-semibold text-ink">{message.artifactKind}</span>
      </div>
      <p className="mt-1 text-[12px] text-muted">Artifact ID: {message.artifactId}</p>
      <p className="mt-2 text-[13px] text-muted-strong">{message.summary}</p>
    </div>
  );
}

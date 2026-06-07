import { AgentStagePanel } from '@/features/agent-audit';

import type { RuntimeAuditNewsItem } from '../../types';
import { toRuntimeAgentAuditStages, toRuntimeAgentAuditSubject } from '../../utils';

interface RuntimeAuditAgentStagePanelProps {
  item: RuntimeAuditNewsItem;
}

export function RuntimeAuditAgentStagePanel({ item }: RuntimeAuditAgentStagePanelProps) {
  return (
    <AgentStagePanel
      stages={toRuntimeAgentAuditStages(item.agent_stages)}
      subject={toRuntimeAgentAuditSubject(item)}
      title="Agent 处理"
    />
  );
}

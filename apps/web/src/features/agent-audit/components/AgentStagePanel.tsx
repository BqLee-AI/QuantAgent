import { Button, Chip, useOverlayState } from '@heroui/react';
import { useState } from 'react';
import { twMerge } from 'tailwind-merge';

import type { AgentAuditStage, AgentAuditSubject } from '../types';
import {
  formatAgentAuditStageKind,
  formatAgentAuditStatus,
  getAgentAuditStatusTone,
} from '../utils';
import { AgentKeyFields } from './AgentKeyFields';
import { AgentStageDetailModal } from './AgentStageDetailModal';
import { AgentAuditEmptyState } from './states';

interface AgentStagePanelProps {
  detailStage?: AgentAuditStage | null;
  onOpenStage?: (stage: AgentAuditStage) => void;
  subject: AgentAuditSubject;
  stages: AgentAuditStage[];
  title?: string;
}

export function AgentStagePanel({ detailStage, onOpenStage, subject, stages, title = 'Agent 处理' }: AgentStagePanelProps) {
  const detailState = useOverlayState();
  const [selectedStage, setSelectedStage] = useState<AgentAuditStage | null>(null);

  if (stages.length === 0) {
    return (
      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">{title}</h3>
        <AgentAuditEmptyState message="后端尚未返回 Agent stage。" />
      </section>
    );
  }

  function openStage(stage: AgentAuditStage) {
    onOpenStage?.(stage);
    setSelectedStage(stage);
    detailState.open();
  }

  const modalStage = detailStage && detailStage.stage_id === selectedStage?.stage_id ? detailStage : (selectedStage ?? null);

  return (
    <section className="grid gap-2">
      <div>
        <h3 className="m-0 text-[13px] font-semibold text-ink">{title}</h3>
        <p className="m-0 mt-1 text-[12px] text-muted">右侧只展示摘要；详细内容通过共享弹窗审计。</p>
      </div>
      <div className="grid gap-3">
        {stages.map((stage) => (
          <article key={stage.stage_id} className="rounded-lg border border-hairline bg-surface-soft px-3 py-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-body-sm font-semibold text-ink">{stage.title}</span>
                  <Chip className={twMerge('text-[11px] font-semibold', getAgentAuditStatusTone(stage.status))} size="sm" variant="soft">
                    {formatAgentAuditStatus(stage.status)}
                  </Chip>
                  <Chip size="sm" variant="soft">{formatAgentAuditStageKind(stage.stage_kind)}</Chip>
                </div>
                <p className="m-0 mt-2 text-body-sm text-muted">{stage.summary || '当前阶段没有处理摘要。'}</p>
                {stage.unavailable_reason ? (
                  <p className="m-0 mt-1 text-[12px] text-muted">{stage.unavailable_reason}</p>
                ) : null}
              </div>
              <Button size="sm" type="button" variant="outline" onPress={() => openStage(stage)}>
                查看处理详情
              </Button>
            </div>
            <div className="mt-3">
              <AgentKeyFields fields={stage.key_fields} />
            </div>
          </article>
        ))}
      </div>
      <AgentStageDetailModal subject={subject} stage={modalStage} state={detailState} />
    </section>
  );
}

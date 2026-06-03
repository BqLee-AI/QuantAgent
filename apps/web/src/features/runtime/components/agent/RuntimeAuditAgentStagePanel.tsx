import { Button, Chip, useOverlayState } from '@heroui/react';
import { useState } from 'react';
import { twMerge } from 'tailwind-merge';

import type { RuntimeAuditAgentStage, RuntimeAuditNewsItem } from '../../types';
import {
  formatRuntimeAuditAgentType,
  formatRuntimeAuditStatus,
  getRuntimeAuditStatusTone,
} from '../../utils';
import { RuntimeAuditAgentDetailModal } from './RuntimeAuditAgentDetailModal';
import { RuntimeAuditAgentKeyFields } from './RuntimeAuditAgentKeyFields';

interface RuntimeAuditAgentStagePanelProps {
  item: RuntimeAuditNewsItem;
}

export function RuntimeAuditAgentStagePanel({ item }: RuntimeAuditAgentStagePanelProps) {
  const detailState = useOverlayState();
  const [selectedStage, setSelectedStage] = useState<RuntimeAuditAgentStage | null>(null);
  const stages = item.agent_stages;

  if (stages.length === 0) {
    return (
      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">Agent 处理</h3>
        <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
          后端尚未返回 Agent stage。
        </p>
      </section>
    );
  }

  function openStage(stage: RuntimeAuditAgentStage) {
    setSelectedStage(stage);
    detailState.open();
  }

  return (
    <section className="grid gap-2">
      <div>
        <h3 className="m-0 text-[13px] font-semibold text-ink">Agent 处理</h3>
        <p className="m-0 mt-1 text-[12px] text-muted">右侧只展示摘要；详细内容通过可复用弹窗审计。</p>
      </div>
      <div className="grid gap-3">
        {stages.map((stage) => (
          <article key={stage.stage_id} className="rounded-lg border border-hairline bg-surface-soft px-3 py-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-body-sm font-semibold text-ink">{stage.agent_name}</span>
                  <Chip className={twMerge('text-[11px] font-semibold', getRuntimeAuditStatusTone(stage.status))} size="sm" variant="soft">
                    {formatRuntimeAuditStatus(stage.status)}
                  </Chip>
                  <Chip size="sm" variant="soft">{formatRuntimeAuditAgentType(stage.agent_type)}</Chip>
                </div>
                <p className="m-0 mt-2 text-body-sm text-muted">{stage.summary}</p>
                {stage.unavailable_reason ? (
                  <p className="m-0 mt-1 text-[12px] text-muted">{stage.unavailable_reason}</p>
                ) : null}
              </div>
              <Button size="sm" type="button" variant="outline" onPress={() => openStage(stage)}>
                查看处理详情
              </Button>
            </div>
            <div className="mt-3">
              <RuntimeAuditAgentKeyFields fields={stage.key_fields} />
            </div>
          </article>
        ))}
      </div>
      <RuntimeAuditAgentDetailModal item={item} stage={selectedStage} state={detailState} />
    </section>
  );
}

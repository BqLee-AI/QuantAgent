import { Chip } from '@heroui/react';
import { twMerge } from 'tailwind-merge';

import type { RuntimeAuditMessage as RuntimeAuditMessageModel } from '../../types';
import {
  formatRuntimeAuditActor,
  formatRuntimeAuditBadge,
  formatRuntimeAuditDate,
  formatRuntimeAuditDecision,
  formatRuntimeAuditStage,
  formatRuntimeAuditStatus,
  getRuntimeAuditDecisionTone,
  getRuntimeAuditStatusTone,
} from '../../utils';

interface RuntimeAuditMessageProps {
  isSelected: boolean;
  message: RuntimeAuditMessageModel;
  onSelect: (messageId: string) => void;
}

export function RuntimeAuditMessage({
  isSelected,
  message,
  onSelect,
}: RuntimeAuditMessageProps) {
  return (
    <button
      className={twMerge(
        'w-full rounded-xl border px-4 py-3 text-left transition-colors',
        isSelected
          ? 'border-primary/35 bg-surface-soft shadow-card'
          : 'border-hairline bg-canvas hover:bg-surface-soft',
      )}
      type="button"
      onClick={() => onSelect(message.id)}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Chip className={twMerge('text-[11px] font-semibold', getRuntimeAuditStatusTone(message.status))} size="sm" variant="soft">
          {formatRuntimeAuditStatus(message.status)}
        </Chip>
        <span className="text-[12px] font-semibold text-muted-strong">
          {formatRuntimeAuditActor(message.actor_type)} · {formatRuntimeAuditStage(message.stage)}
        </span>
        <span className="text-[12px] text-muted">{formatRuntimeAuditDate(message.occurred_at)}</span>
      </div>
      <div className="mt-2 grid gap-1">
        <h3 className="m-0 text-title-sm font-semibold text-ink">{message.title}</h3>
        <p className="m-0 text-body-sm text-muted">{message.summary}</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {message.decision ? (
          <span className={twMerge('rounded-full border px-2.5 py-1 text-[12px] font-semibold', getRuntimeAuditDecisionTone(message.decision))}>
            {formatRuntimeAuditDecision(message.decision)}
          </span>
        ) : null}
        {message.badges.map((badge) => (
          <span key={badge} className="rounded-full border border-hairline bg-surface-card px-2.5 py-1 text-[12px] font-semibold text-muted-strong">
            {formatRuntimeAuditBadge(badge)}
          </span>
        ))}
      </div>
    </button>
  );
}

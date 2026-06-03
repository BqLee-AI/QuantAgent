import { Chip } from '@heroui/react';
import { twMerge } from 'tailwind-merge';

import type { RuntimeAuditNewsItem } from '../../types';
import {
  formatRuntimeAuditDate,
  formatRuntimeAuditStage,
  formatRuntimeAuditStatus,
  formatRuntimeAuditTimeline,
  getRuntimeAuditStageTone,
  getRuntimeAuditStatusTone,
} from '../../utils';

interface RuntimeAuditMessageProps {
  isSelected: boolean;
  item: RuntimeAuditNewsItem;
  onSelect: (rawEventId: string) => void;
}

export function RuntimeAuditMessage({
  isSelected,
  item,
  onSelect,
}: RuntimeAuditMessageProps) {
  const title = item.title || item.canonical_url || item.raw_event_id;
  const sourceLine = [
    item.source_name ?? item.source_plugin_id,
    item.published_at ? `发布 ${formatRuntimeAuditDate(item.published_at)}` : null,
    item.url_host,
  ].filter(Boolean).join(' · ');

  return (
    <button
      className={twMerge(
        'w-full rounded-xl border px-4 py-3 text-left transition-colors',
        isSelected
          ? 'border-primary/35 bg-surface-soft shadow-card'
          : 'border-hairline bg-canvas hover:bg-surface-soft',
      )}
      type="button"
      onClick={() => onSelect(item.raw_event_id)}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Chip className={twMerge('text-[11px] font-semibold', getRuntimeAuditStatusTone(item.status))} size="sm" variant="soft">
          {formatRuntimeAuditStatus(item.status)}
        </Chip>
        <span className={twMerge('rounded-full border px-2.5 py-1 text-[12px] font-semibold', getRuntimeAuditStageTone(item.focus_stage))}>
          重点：{formatRuntimeAuditStage(item.focus_stage)}
        </span>
      </div>
      <div className="mt-2 grid gap-1">
        <h3 className="m-0 text-title-sm font-semibold text-ink">{title}</h3>
        <p className="m-0 text-body-sm text-muted">{sourceLine || '来源信息不足'}</p>
      </div>
      <div className="mt-3 rounded-lg border border-hairline bg-surface-card px-3 py-2 text-[12px] text-muted-strong">
        {formatRuntimeAuditTimeline(item.timeline)}
      </div>
    </button>
  );
}

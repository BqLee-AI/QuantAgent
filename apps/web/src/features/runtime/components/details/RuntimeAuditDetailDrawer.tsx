import { Chip } from '@heroui/react';

import type {
  RuntimeAuditMessage,
  RuntimeAuditMessageGroup,
} from '../../types';
import {
  formatRuntimeAuditActor,
  formatRuntimeAuditDate,
  formatRuntimeAuditStage,
  formatRuntimeAuditStatus,
} from '../../utils';
import { RuntimeAuditSafeDetails } from './RuntimeAuditSafeDetails';
import { RuntimeAuditTracePanel } from './RuntimeAuditTracePanel';

interface RuntimeAuditDetailDrawerProps {
  group: RuntimeAuditMessageGroup | null;
  message: RuntimeAuditMessage | null;
}

export function RuntimeAuditDetailDrawer({
  group,
  message,
}: RuntimeAuditDetailDrawerProps) {
  if (!message) {
    return (
      <aside className="rounded-xl border border-hairline bg-canvas p-4 text-body-sm text-muted">
        选择一条审计消息查看安全详情。
      </aside>
    );
  }

  return (
    <aside className="grid gap-4 rounded-xl border border-hairline bg-canvas p-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto">
      <div className="grid gap-2">
        <div className="flex flex-wrap gap-2">
          <Chip size="sm" variant="soft">{formatRuntimeAuditStatus(message.status)}</Chip>
          <Chip size="sm" variant="soft">{formatRuntimeAuditActor(message.actor_type)}</Chip>
        </div>
        <h2 className="m-0 text-title-sm font-semibold text-ink">{message.title}</h2>
        <p className="m-0 text-body-sm text-muted">{message.summary}</p>
        <p className="m-0 text-[12px] text-muted">
          {formatRuntimeAuditStage(message.stage)} · {formatRuntimeAuditDate(message.occurred_at)}
        </p>
      </div>

      {group ? (
        <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
          <p className="m-0 text-[12px] font-semibold text-muted-strong">消息组</p>
          <p className="m-0 mt-1 text-body-sm text-ink">{group.source_title}</p>
        </div>
      ) : null}

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">Trace</h3>
        <RuntimeAuditTracePanel trace={message.trace} />
      </section>

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">安全详情</h3>
        {/* 中文注释：Runtime 审计详情只展示 safe_details，避免把 raw prompt / provider raw response 带入前端。 */}
        <RuntimeAuditSafeDetails details={message.safe_details} />
      </section>
    </aside>
  );
}

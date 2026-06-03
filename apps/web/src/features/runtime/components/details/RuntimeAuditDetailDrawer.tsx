import { Chip } from '@heroui/react';
import { twMerge } from 'tailwind-merge';

import type { RuntimeAuditNewsItem } from '../../types';
import {
  formatRuntimeAuditDate,
  formatRuntimeAuditStage,
  formatRuntimeAuditStatus,
  getRuntimeAuditStatusTone,
} from '../../utils';
import { RuntimeAuditAgentStagePanel } from '../agent';
import { RuntimeAuditSafeDetails } from './RuntimeAuditSafeDetails';
import { RuntimeAuditTracePanel } from './RuntimeAuditTracePanel';

interface RuntimeAuditDetailDrawerProps {
  item: RuntimeAuditNewsItem | null;
}

export function RuntimeAuditDetailDrawer({ item }: RuntimeAuditDetailDrawerProps) {
  if (!item) {
    return (
      <aside className="rounded-xl border border-hairline bg-canvas p-4 text-body-sm text-muted">
        选择一篇新闻查看 RawEvent 审计详情。
      </aside>
    );
  }

  const title = item.title || item.canonical_url || item.raw_event_id;
  const unavailableStep = item.timeline.find((step) => step.status === 'unavailable');

  return (
    <aside className="grid gap-4 rounded-xl border border-hairline bg-canvas p-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto">
      <section className="grid gap-2">
        <div className="flex flex-wrap gap-2">
          <Chip className={twMerge('text-[11px] font-semibold', getRuntimeAuditStatusTone(item.status))} size="sm" variant="soft">
            {formatRuntimeAuditStatus(item.status)}
          </Chip>
          <Chip size="sm" variant="soft">{formatRuntimeAuditStage(item.current_stage)}</Chip>
        </div>
        <h2 className="m-0 text-title-sm font-semibold text-ink">{title}</h2>
        <a className="break-all text-body-sm text-info" href={item.canonical_url ?? undefined} rel="noreferrer" target="_blank">
          {item.canonical_url ?? '无 URL'}
        </a>
        <dl className="grid gap-1 text-body-sm text-muted">
          <MetaRow label="来源" value={item.source_name ?? item.source_plugin_id} />
          <MetaRow label="作者" value={item.author ?? '未记录'} />
          <MetaRow label="发布时间" value={formatRuntimeAuditDate(item.published_at)} />
          <MetaRow label="捕获时间" value={formatRuntimeAuditDate(item.last_captured_at)} />
        </dl>
        <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
          {item.content_preview ?? '列表接口没有返回正文预览。'}
        </p>
      </section>

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">当前进度</h3>
        <div className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
          <p className="m-0 font-semibold text-ink">
            当前：{formatRuntimeAuditStage(item.current_stage)} / 重点：{formatRuntimeAuditStage(item.focus_stage)}
          </p>
          <p className="m-0 mt-1">
            {unavailableStep?.summary ?? '当前可确认阶段均有持久化事实。'}
          </p>
        </div>
      </section>

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">Timeline</h3>
        <ol className="m-0 grid list-none gap-2 p-0">
          {item.timeline.map((step) => (
            <li key={step.step_id} className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-body-sm font-semibold text-ink">{step.label}</span>
                <span className={twMerge('rounded-full border px-2 py-0.5 text-[11px] font-semibold', getRuntimeAuditStatusTone(step.status))}>
                  {formatRuntimeAuditStatus(step.status)}
                </span>
              </div>
              <p className="m-0 mt-1 text-body-sm text-muted">{step.summary}</p>
              <p className="m-0 mt-1 text-[12px] text-muted">{formatRuntimeAuditDate(step.occurred_at)}</p>
              {step.refs.length > 0 ? (
                <p className="m-0 mt-1 break-all font-mono text-[11px] text-muted">
                  {step.refs.map((ref) => `${ref.kind}:${ref.id}`).join(' / ')}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">Trace</h3>
        <RuntimeAuditTracePanel trace={item.trace} />
      </section>

      <RuntimeAuditAgentStagePanel item={item} />

      <section className="grid gap-2">
        <h3 className="m-0 text-[13px] font-semibold text-ink">安全详情</h3>
        {/* 中文注释：Runtime 默认详情只展示 allowlisted metadata，不展示完整 content/raw_payload。 */}
        <RuntimeAuditSafeDetails details={item.safe_details} />
      </section>
    </aside>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
      <dt className="font-semibold text-muted-strong">{label}</dt>
      <dd className="m-0 break-words">{value}</dd>
    </div>
  );
}

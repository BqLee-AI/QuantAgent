import { Button, Chip, Modal, useOverlayState } from '@heroui/react';
import { twMerge } from 'tailwind-merge';

import type { RuntimeAuditAgentStage, RuntimeAuditNewsItem } from '../../types';
import {
  formatRuntimeAuditAgentType,
  formatRuntimeAuditDate,
  formatRuntimeAuditStatus,
  getRuntimeAuditStatusTone,
} from '../../utils';
import { RuntimeAuditAgentJsonView } from './RuntimeAuditAgentJsonView';
import { RuntimeAuditAgentKeyFields } from './RuntimeAuditAgentKeyFields';

interface RuntimeAuditAgentDetailModalProps {
  item: RuntimeAuditNewsItem;
  stage: RuntimeAuditAgentStage | null;
  state: ReturnType<typeof useOverlayState>;
}

export function RuntimeAuditAgentDetailModal({
  item,
  stage,
  state,
}: RuntimeAuditAgentDetailModalProps) {
  if (!stage) {
    return null;
  }

  const title = item.title || item.canonical_url || item.raw_event_id;

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog className="w-full max-w-[min(76rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <div className="min-w-0">
                <Modal.Heading>{stage.agent_name} 处理详情</Modal.Heading>
                <p className="m-0 mt-1 truncate text-body-sm text-muted">{title}</p>
              </div>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="max-h-[calc(100vh-9rem)] overflow-y-auto px-5 py-4">
              <div className="grid gap-4">
                <section className="grid gap-2 rounded-xl border border-hairline bg-canvas p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip className={twMerge('text-[11px] font-semibold', getRuntimeAuditStatusTone(stage.status))} size="sm" variant="soft">
                      {formatRuntimeAuditStatus(stage.status)}
                    </Chip>
                    <Chip size="sm" variant="soft">{formatRuntimeAuditAgentType(stage.agent_type)}</Chip>
                  </div>
                  <h3 className="m-0 text-title-sm font-semibold text-ink">{title}</h3>
                  <a className="break-all text-body-sm text-info" href={item.canonical_url ?? undefined} rel="noreferrer" target="_blank">
                    {item.canonical_url ?? '无 URL'}
                  </a>
                  <div className="grid gap-1 text-body-sm text-muted sm:grid-cols-2">
                    <span>来源：{item.source_name ?? item.source_plugin_id}</span>
                    <span>发布时间：{formatRuntimeAuditDate(item.published_at)}</span>
                    <span>RawEvent：{item.raw_event_id}</span>
                    <span>Binding：{item.trace.binding_id ?? '未记录'}</span>
                  </div>
                  <details className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
                    <summary className="cursor-pointer font-semibold text-ink">展开列表级内容预览</summary>
                    <p className="m-0 mt-2 whitespace-pre-wrap">{item.content_preview ?? '当前列表接口没有返回内容预览。'}</p>
                  </details>
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">处理摘要</h3>
                  <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
                    {stage.summary}
                  </p>
                  {stage.unavailable_reason ? (
                    <p className="m-0 rounded-lg border border-hairline bg-amber-50 px-3 py-2 text-body-sm text-amber-700">
                      {stage.unavailable_reason}
                    </p>
                  ) : null}
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">关键字段</h3>
                  <RuntimeAuditAgentKeyFields fields={stage.key_fields} />
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">完整结构化 Output JSON</h3>
                  {/* 中文注释：这里展示的是 Agent 结构化输出，不展示 provider raw response、CoT 或 secret-bearing runtime object。 */}
                  <RuntimeAuditAgentJsonView value={stage.output_json} />
                </section>

                {stage.refs.length > 0 ? (
                  <section className="grid gap-2">
                    <h3 className="m-0 text-[13px] font-semibold text-ink">可审计引用</h3>
                    <div className="grid gap-2">
                      {stage.refs.map((ref) => (
                        <div key={`${ref.kind}:${ref.id}`} className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 font-mono text-[12px] text-muted">
                          {ref.label}: {ref.kind}:{ref.id}
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            </Modal.Body>
            <Modal.Footer className="border-t border-hairline px-5 py-4">
              <Button variant="outline" onPress={state.close}>关闭</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}

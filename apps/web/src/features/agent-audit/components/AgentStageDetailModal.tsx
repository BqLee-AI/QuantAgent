import { Button, Chip, Modal, useOverlayState } from '@heroui/react';
import { twMerge } from 'tailwind-merge';

import type { AgentAuditStage, AgentAuditSubject } from '../types';
import {
  formatAgentAuditDate,
  formatAgentAuditStageKind,
  formatAgentAuditStatus,
  getAgentAuditStatusTone,
} from '../utils';
import { AgentJsonView } from './AgentJsonView';
import { AgentKeyFields } from './AgentKeyFields';
import { AgentTraceRefs } from './AgentTraceRefs';

interface AgentStageDetailModalProps {
  subject: AgentAuditSubject;
  stage: AgentAuditStage | null;
  state: ReturnType<typeof useOverlayState>;
}

export function AgentStageDetailModal({ subject, stage, state }: AgentStageDetailModalProps) {
  if (!stage) {
    return null;
  }

  const title = subject.title || subject.url || subject.subject_id;
  const source = subject.source ?? subject.source_plugin_id ?? '未记录来源';

  return (
    <Modal state={state}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog className="w-full max-w-[min(76rem,calc(100vw-2rem))] overflow-hidden">
            <Modal.Header className="border-b border-hairline px-5 py-4">
              <div className="min-w-0">
                <Modal.Heading>{stage.title} 处理详情</Modal.Heading>
                <p className="m-0 mt-1 truncate text-body-sm text-muted">{title}</p>
              </div>
              <Modal.CloseTrigger aria-label="关闭" />
            </Modal.Header>
            <Modal.Body className="max-h-[calc(100vh-9rem)] overflow-y-auto px-5 py-4">
              <div className="grid gap-4">
                <section className="grid gap-2 rounded-xl border border-hairline bg-canvas p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip className={twMerge('text-[11px] font-semibold', getAgentAuditStatusTone(stage.status))} size="sm" variant="soft">
                      {formatAgentAuditStatus(stage.status)}
                    </Chip>
                    <Chip size="sm" variant="soft">{formatAgentAuditStageKind(stage.stage_kind)}</Chip>
                  </div>
                  <h3 className="m-0 text-title-sm font-semibold text-ink">{title}</h3>
                  <a className="break-all text-body-sm text-info" href={subject.url ?? undefined} rel="noreferrer" target="_blank">
                    {subject.url ?? '无 URL'}
                  </a>
                  <div className="grid gap-1 text-body-sm text-muted sm:grid-cols-2">
                    <span>来源：{source}</span>
                    <span>发布时间：{formatAgentAuditDate(subject.published_at)}</span>
                    <span>Subject：{subject.subject_id}</span>
                    <span>Trace：{subject.trace?.trace_id ?? subject.trace?.request_id ?? '未记录'}</span>
                  </div>
                  <details className="rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
                    <summary className="cursor-pointer font-semibold text-ink">展开列表级内容预览</summary>
                    <p className="m-0 mt-2 whitespace-pre-wrap">{subject.content_preview ?? '当前接口没有返回安全内容预览。'}</p>
                  </details>
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">处理摘要</h3>
                  <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
                    {stage.summary || '当前阶段没有处理摘要。'}
                  </p>
                  {stage.unavailable_reason ? (
                    <p className="m-0 rounded-lg border border-hairline bg-amber-50 px-3 py-2 text-body-sm text-amber-700">
                      {stage.unavailable_reason}
                    </p>
                  ) : null}
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">关键字段</h3>
                  <AgentKeyFields fields={stage.key_fields} />
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">完整结构化 Output JSON</h3>
                  {/* 中文注释：这里只渲染安全结构化输出；raw response、prompt、CoT、secret 和完整正文必须留在 mapper/API 安全边界外。 */}
                  <AgentJsonView value={stage.output_json} />
                </section>

                <section className="grid gap-2">
                  <h3 className="m-0 text-[13px] font-semibold text-ink">可审计引用</h3>
                  <AgentTraceRefs refs={stage.refs} />
                </section>
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

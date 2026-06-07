import { Chip } from '@heroui/react';

import { AgentJsonView, AgentStagePanel, type AgentAuditStage } from '@/features/agent-audit';
import { LinkButton, PageHeader, PageSectionCard, SectionHeader } from '@/shared/ui';

import { useEventDetailPage } from '../../hooks';
import type { EventAgentStage, EventDetailResponse } from '../../types';
import {
  eventDecisionTone,
  eventStatusTone,
  formatEventDate,
  formatEventDecision,
  formatEventStatus,
  toEventAgentAuditStages,
  toEventAgentAuditSubject,
  toAgentAuditSafeRecord,
} from '../../utils';

export function EventDetailPage({ rawEventId }: { rawEventId: string }) {
  const page = useEventDetailPage(rawEventId);
  const detail = page.detailQuery.data;

  if (page.detailQuery.isLoading) {
    return <EventDetailState title="正在加载事件详情" description="正在读取 Router Agent 处理结果。" />;
  }
  if (page.detailQuery.isError || !detail) {
    return (
      <EventDetailState
        title="事件不存在或不可访问"
        description={page.detailQuery.error instanceof Error ? page.detailQuery.error.message : '没有找到已路由事件。未处理新闻请到运行态页面排查。'}
      />
    );
  }

  return (
    <EventDetailContent
      detail={detail}
      onOpenAgentStage={(stage) => selectAgentStage(detail.agent_stages, stage, page.setSelectedAgentStage)}
      selectedAgentStage={page.selectedAgentStage}
      selectedRouterOutput={page.routerOutputQuery}
    />
  );
}

export function EventAuditPage({ rawEventId }: { rawEventId: string }) {
  const page = useEventDetailPage(rawEventId);
  const detail = page.detailQuery.data;

  if (page.detailQuery.isLoading) {
    return <EventDetailState title="正在加载审计详情" description="正在读取 Router Agent 时间线。" />;
  }
  if (page.detailQuery.isError || !detail) {
    return <EventDetailState title="审计详情不可用" description="没有找到已路由事件，或当前账号无权查看。" />;
  }

  return (
    <div className="grid gap-5">
      <PageHeader kicker="事件审计" title={detail.title ?? detail.raw_event_id} />
      <PageSectionCard>
        <SectionHeader eyebrow="Router Agent Timeline" title="已持久化阶段" />
        <div className="grid gap-3">
          {detail.timeline.map((step) => (
            <article key={step.step_id} className="grid gap-1.5 border-l-2 border-hairline-strong pl-3.5">
              <p className="m-0 text-[12px] font-bold text-muted">{step.label} · {formatEventStatus(step.status)}</p>
              <p className="m-0 text-body-sm text-muted">{step.summary}</p>
              <p className="m-0 font-mono text-[12px] text-muted">{step.refs.map((ref) => `${ref.kind}:${ref.id}`).join(' · ')}</p>
            </article>
          ))}
        </div>
      </PageSectionCard>
      <SharedRouterStageSection
        detail={detail}
        onOpenAgentStage={(stage) => selectAgentStage(detail.agent_stages, stage, page.setSelectedAgentStage)}
        selectedAgentStage={page.selectedAgentStage}
        selectedRouterOutput={page.routerOutputQuery}
      />
    </div>
  );
}

function EventDetailContent({
  detail,
  onOpenAgentStage,
  selectedAgentStage,
  selectedRouterOutput,
}: {
  detail: EventDetailResponse;
  onOpenAgentStage: (stage: AgentAuditStage) => void;
  selectedAgentStage: EventAgentStage | null;
  selectedRouterOutput: ReturnType<typeof useEventDetailPage>['routerOutputQuery'];
}) {
  return (
    <div className="grid gap-5">
      <PageHeader kicker="事件详情" title={detail.title ?? detail.raw_event_id} />

      <PageSectionCard>
        <SectionHeader eyebrow="新闻摘要" title={detail.summary ?? 'Router Agent 未返回摘要'} />
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className={eventDecisionTone(detail.decision)} size="sm" variant="soft">{formatEventDecision(detail.decision)}</Chip>
            <Chip className={eventStatusTone(detail.status)} size="sm" variant="soft">{formatEventStatus(detail.status)}</Chip>
            <Chip size="sm" variant="soft">{detail.priority ?? 'normal'}</Chip>
          </div>
          <div className="grid gap-1 text-body-sm text-muted sm:grid-cols-2">
            <span>来源：{detail.source_name ?? detail.source_plugin_id ?? '未知'}</span>
            <span>发布时间：{formatEventDate(detail.published_at)}</span>
            <span>路由时间：{formatEventDate(detail.routed_at)}</span>
            <span>关系：{detail.relationship_summary ?? '未记录'}</span>
          </div>
          {detail.url ? <a className="break-all text-body-sm text-info" href={detail.url} rel="noreferrer" target="_blank">{detail.url}</a> : null}
        </div>
      </PageSectionCard>

      <SharedRouterStageSection
        detail={detail}
        onOpenAgentStage={onOpenAgentStage}
        selectedAgentStage={selectedAgentStage}
        selectedRouterOutput={selectedRouterOutput}
      />

      <PageSectionCard>
        <SectionHeader eyebrow="Trace" title="可审计引用" />
        <div className="grid gap-2 font-mono text-[12px] text-muted">
          <span>raw_event_id: {detail.trace.raw_event_id}</span>
          <span>routed_event_id: {detail.trace.routed_event_id}</span>
          <span>binding_id: {detail.trace.binding_id ?? '未记录'}</span>
          <span>request_id: {detail.trace.request_id ?? '未记录'}</span>
          <span>correlation_id: {detail.trace.correlation_id ?? '未记录'}</span>
        </div>
      </PageSectionCard>

      <PageSectionCard>
        <SectionHeader eyebrow="安全详情" title="后端允许展示的安全摘要" />
        <AgentJsonView value={toAgentAuditSafeRecord(detail.safe_details)} />
      </PageSectionCard>

      <div className="flex flex-wrap gap-2">
        <LinkButton to="/events" variant="outline">返回事件中心</LinkButton>
        <LinkButton to="/runtime" variant="outline">去运行态排障</LinkButton>
      </div>
    </div>
  );
}

function SharedRouterStageSection({
  detail,
  onOpenAgentStage,
  selectedAgentStage,
  selectedRouterOutput,
}: {
  detail: EventDetailResponse;
  onOpenAgentStage: (stage: AgentAuditStage) => void;
  selectedAgentStage: EventAgentStage | null;
  selectedRouterOutput: ReturnType<typeof useEventDetailPage>['routerOutputQuery'];
}) {
  const output = selectedRouterOutput.data;
  const subject = toEventAgentAuditSubject(detail);
  const stages = toEventAgentAuditStages(detail.agent_stages, output);
  const selectedStage = buildSelectedAuditStage(stages, selectedAgentStage, selectedRouterOutput);

  return (
    <PageSectionCard>
      <SectionHeader eyebrow="Agent 处理" title="Router Agent 输出" />
      <AgentStagePanel
        detailStage={selectedStage}
        onOpenStage={onOpenAgentStage}
        stages={stages}
        subject={subject}
        title="Router Agent 审计"
      />
    </PageSectionCard>
  );
}

function buildSelectedAuditStage(
  stages: AgentAuditStage[],
  selectedAgentStage: EventAgentStage | null,
  selectedRouterOutput: ReturnType<typeof useEventDetailPage>['routerOutputQuery'],
) {
  if (!selectedAgentStage) return null;
  const stage = stages.find((item) => item.stage_id === selectedAgentStage.stage_id);
  if (!stage) return null;
  if (selectedRouterOutput.isLoading) {
    return {
      ...stage,
      output_json: {
        status: 'loading',
        message: '正在按需读取 Router Agent 完整结构化 output JSON。',
      },
    } satisfies AgentAuditStage;
  }
  if (selectedRouterOutput.isError) {
    return {
      ...stage,
      output_json: null,
      unavailable_reason: selectedRouterOutput.error instanceof Error
        ? selectedRouterOutput.error.message
        : 'Router Agent output detail 暂不可用。',
    } satisfies AgentAuditStage;
  }
  if (!selectedAgentStage.has_output_json) {
    return {
      ...stage,
      output_json: null,
      unavailable_reason: stage.unavailable_reason ?? '后端没有持久化完整 Router Agent output JSON。',
    } satisfies AgentAuditStage;
  }
  return stage;
}

function selectAgentStage(
  stages: EventAgentStage[],
  stage: AgentAuditStage,
  setSelectedAgentStage: (stage: EventAgentStage | null) => void,
) {
  setSelectedAgentStage(stages.find((item) => item.stage_id === stage.stage_id) ?? null);
}

function EventDetailState({ description, title }: { description: string; title: string }) {
  return (
    <div className="grid gap-5">
      <PageHeader kicker="事件详情" title={title} description={description} />
      <PageSectionCard>
        <div className="flex flex-wrap gap-2">
          <LinkButton to="/events" variant="outline">返回事件中心</LinkButton>
          <LinkButton to="/runtime" variant="outline">去运行态排障</LinkButton>
        </div>
      </PageSectionCard>
    </div>
  );
}

import { featuredEvents, healthAlerts, approvalsQueue } from '../mock-data'
import { EventCard } from '../components/EventCard'
import { LinkButton } from '../components/LinkButton'
import { PageSectionCard } from '../components/PageSectionCard'
import { SectionHeader } from '../components/SectionHeader'
import { DetailFacts, InfoTag, PageHeader } from './shared'

export function EventsIndexPageContent() {
  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件中心"
        title="高价值事件"
        description="从 Dashboard 进入后的事件浏览和筛选页。这里负责扩展视野，不承担首页总控职责。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="筛选与排序"
            title="首版只落结构，不发明 API shape"
            description="时间范围、半导体子行业、参考强度、分析状态和来源类型将进入 URL search params；本轮先用静态骨架表达信息架构。"
          />
          <div className="flex flex-wrap gap-2">
            {['时间范围', '半导体子行业', '参考强度', '分析状态', '最新 + 高价值'].map((item) => (
              <InfoTag key={item}>{item}</InfoTag>
            ))}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="系统提醒"
            title="轻量异常摘要"
            description="只做浏览过程中的轻提示，不把运行态排障台塞回事件中心。"
          />
          <div className="grid gap-2">
            <EventCard
              event={{
                ...featuredEvents[0]!,
                id: healthAlerts[0]!.id,
                title: healthAlerts[0]!.title,
                summary: healthAlerts[0]!.summary,
                actionHint: healthAlerts[0]!.traceHint,
                industryImpact: '运行风险提示',
                industries: ['Runtime'],
                priority: healthAlerts[0]!.severity,
                source: '系统健康',
                status: 'warning',
                referenceStrength: '内部',
              }}
              toDetail={false}
            />
          </div>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="重点事件"
          title="重点事件区与完整列表并存"
          description="重点区解释为什么值得先看，列表承担稳定跳转到事件详情。"
        />
        <div className="grid gap-3">
          {featuredEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </PageSectionCard>
    </div>
  )
}

export function EventDetailPageContent({ eventId }: { eventId: string }) {
  const event = featuredEvents.find((item) => item.id === eventId) ?? featuredEvents[0]!
  const relatedApproval = approvalsQueue.find((item) => item.eventTitle === event.title) ?? null

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件详情 / 决策"
        title={event.title}
        description="事件事实、行业影响分析和最佳动作建议必须分区展示；本页不直接批准或执行高风险动作。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="事件事实"
            title="左栏先给事实和验证状态"
            description="事实区保留来源、发布时间、事件状态和可信度摘要。"
          />
          <DetailFacts
            rows={[
              `来源：${event.source}`,
              `发布时间：${event.publishedAt}`,
              `当前状态：${event.status}`,
              `参考强度：${event.referenceStrength}`,
              `事件概括：${event.summary}`,
            ]}
          />
          <div className="flex flex-wrap gap-2">
            <LinkButton to="/events" variant="outline">返回事件中心</LinkButton>
            <LinkButton to="/events/$eventId/audit" params={{ eventId: event.id }} variant="outline">
              审计时间线
            </LinkButton>
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="行业影响与最佳动作"
            title="右栏首屏优先展示分析和动作"
            description="首版只展示一个最佳动作，不做多候选动作比较工作台。"
          />
          <DetailFacts
            rows={[
              `影响行业：${event.industries.join(' / ')}`,
              `影响方向：${event.industryImpact}`,
              `建议动作：${event.actionHint}，等待审批确认后进入受控链路。`,
              '风险摘要：需要 strong_confirm，且当前建议不等于真实执行完成。',
            ]}
          />
          <div className="flex flex-wrap gap-2">
            {relatedApproval ? (
              <LinkButton to="/approvals/$approvalId" params={{ approvalId: relatedApproval.id }}>
                进入审批
              </LinkButton>
            ) : (
              <InfoTag>当前事件暂无关联审批</InfoTag>
            )}
            <LinkButton to="/runtime" variant="outline">查看运行摘要</LinkButton>
          </div>
        </PageSectionCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="支持 / 反方观点"
            title="只展示结构化摘要"
            description="不展示完整 chain-of-thought，也不回放原始长推理文本。"
          />
          <ul className="m-0 grid list-none gap-3 p-0">
            {[
              ['支持观点', '出口限制升级直接压缩设备与上游材料板块未来两周风险偏好。'],
              ['反方观点', '若后续出现政策缓释或国产替代加速，板块回撤可能快于预期。'],
              ['数据缺口', '还缺少二级供应链价格与跨行业对冲信号。'],
            ].map(([label, text]) => (
              <li key={label} className="grid gap-1.5 border-l-2 border-hairline-strong pl-3.5">
                <p className="m-0 text-[12px] font-bold text-muted">{label}</p>
                <p className="m-0 text-body-sm text-muted">{text}</p>
              </li>
            ))}
          </ul>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="运行摘要"
            title="把 trace / request 入口留给 Runtime"
            description="详情页只给结构化摘要和入口，不替代运行态诊断界面。"
          />
          <DetailFacts
            rows={[
              '关联 Agent Run：2',
              '最近分析状态：decision_ready',
              '关键工具失败：0',
              'trace_id 占位：rt-mainflow-evt-001',
            ]}
          />
        </PageSectionCard>
      </section>
    </div>
  )
}

export function EventAuditPageContent({ eventId }: { eventId: string }) {
  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件级审计"
        title="事件时间线"
        description="按事件回放建议、重分析和人工动作。这里只做时间线骨架，不发明新的审计 contract。"
      />

      <PageSectionCard>
        <SectionHeader
          eyebrow="Audit"
          title={`事件 ${eventId} 的关键节点`}
          description="真实审计记录以后端真源为准；本轮先把入口和阅读顺序落地。"
        />
        <div className="grid gap-3">
          {[
            ['10:24 · 事件采集', 'Source 插件捕获事件并进入路由阶段。'],
            ['10:31 · 影响分析完成', '行业影响分析输出结构化摘要并生成最佳动作候选。'],
            ['10:36 · 审批请求生成', '高风险建议已进入人工确认链路，等待 strong_confirm。'],
          ].map(([title, copy]) => (
            <article key={title} className="grid gap-1.5 border-l-2 border-hairline-strong pl-3.5">
              <p className="m-0 text-[12px] font-bold text-muted">{title}</p>
              <p className="m-0 text-body-sm text-muted">{copy}</p>
            </article>
          ))}
        </div>
      </PageSectionCard>
    </div>
  )
}

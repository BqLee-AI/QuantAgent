import {
  Button,
  Chip,
} from '@heroui/react'
import { Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import styles from './MainflowPage.module.css'
import {
  approvalsQueue,
  dashboardMetrics,
  featuredEvents,
  healthAlerts,
  type ApprovalSummary,
  type EventSummary,
  type HealthAlert,
  walletMetrics,
  walletTrend,
} from './mock-data'

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <header className={styles.panelHeader}>
      <div>
        <p className={styles.sectionEyebrow}>{eyebrow}</p>
        <h2 className={styles.sectionTitle}>{title}</h2>
        <p className={styles.sectionCopy}>{description}</p>
      </div>
      {action}
    </header>
  )
}

function EventCard({ event, toDetail = true }: { event: EventSummary; toDetail?: boolean }) {
  const relativeTime =
    event.publishedMinutesAgo >= 60
      ? `${Math.floor(event.publishedMinutesAgo / 60)} 小时前`
      : `${event.publishedMinutesAgo} 分钟前`

  return (
    <article className={styles.eventCard}>
      <div className={styles.eventCardTopline}>
        <div className={styles.compactTags}>
          <span className={styles.signalTag}>{event.priority}</span>
          <span className={styles.contextTag}>参考强度 {event.referenceStrength}</span>
          <span className={styles.contextTag}>状态 {event.status}</span>
        </div>
        <span className={styles.impactTag}>{event.industryImpact}</span>
      </div>
      <div className={styles.eventCardBody}>
        <div className={styles.eventHeadlineBlock}>
          <h3 className={styles.eventTitle}>{event.title}</h3>
          <p className={styles.eventTime}>
            {relativeTime} · {event.source}
          </p>
        </div>
        <p className={styles.eventSummary}>{event.summary}</p>
        <div className={styles.eventFooterMeta}>
          <div className={styles.tagRow}>
            {event.industries.map((industry) => (
              <span key={industry} className={styles.microTag}>
                {industry}
              </span>
            ))}
          </div>
          <p className={styles.eventActionHint}>{event.actionHint}</p>
        </div>
      </div>
      {toDetail ? (
        <div className={styles.actionRow}>
          <Link className={styles.actionLink} to="/events/$eventId" params={{ eventId: event.id }}>
            查看分析
          </Link>
          <Link className={styles.secondaryLink} to="/events/$eventId/audit" params={{ eventId: event.id }}>
            审计时间线
          </Link>
        </div>
      ) : null}
    </article>
  )
}

function WalletPnlChart() {
  const maxMagnitude = Math.max(...walletTrend.map((item) => Math.abs(item.pnl)))

  return (
    <div className={styles.walletChart}>
      {walletTrend.map((item) => {
        const isNegative = item.pnl < 0
        const height = `${Math.max((Math.abs(item.pnl) / maxMagnitude) * 100, 18)}%`

        return (
          <div key={item.day} className={styles.walletBarColumn}>
            <p className={styles.walletBarValue}>
              {item.pnl > 0 ? '+' : '-'}¥ {Math.abs(item.pnl).toLocaleString('en-US')}
            </p>
            <div className={styles.walletBarTrack}>
              <div
                className={isNegative ? styles.walletBarNegative : styles.walletBarPositive}
                style={{ height }}
              />
            </div>
            <p className={styles.walletBarLabel}>{item.day}</p>
          </div>
        )
      })}
    </div>
  )
}

function ApprovalCard({ approval }: { approval: ApprovalSummary }) {
  return (
    <article className={styles.compactPanel}>
      <div className={styles.listMeta}>
        <span className={styles.tag}>{approval.riskDirection}</span>
        <span className={styles.tag}>{approval.riskLevel}</span>
        <span className={styles.tag}>{approval.confirmationLevel}</span>
      </div>
      <div>
        <h3 className={styles.listTitle}>{approval.actionLabel}</h3>
        <p className={styles.itemMeta}>
          {approval.eventTitle} · {approval.recommendation} · {approval.expiresIn}
        </p>
      </div>
      <div className={styles.actionRow}>
        <Link
          className={styles.actionLink}
          to="/approvals/$approvalId"
          params={{ approvalId: approval.id }}
        >
          查看审批
        </Link>
        <Link className={styles.secondaryLink} to="/approvals">
          回到审批队列
        </Link>
      </div>
    </article>
  )
}

function HealthCard({ alert }: { alert: HealthAlert }) {
  return (
    <article className={styles.compactPanel}>
      <div className={styles.listMeta}>
        <span className={styles.tag}>{alert.severity}</span>
      </div>
      <div>
        <h3 className={styles.listTitle}>{alert.title}</h3>
        <p className={styles.itemBody}>{alert.summary}</p>
      </div>
      <p className={styles.itemMeta}>{alert.traceHint}</p>
      <Link className={styles.secondaryLink} to="/runtime">
        进入运行态
      </Link>
    </article>
  )
}

export function DashboardPageContent() {
  return (
    <div className={styles.dashboardShell}>
      <header className={`${styles.newsHeader} ${styles.dashboardHero}`}>
        <div className={styles.newsHeaderMain}>
          <p className={styles.newsKicker}>Dashboard</p>
          <h1 className={styles.newsHeroTitle}>半导体新闻流</h1>
          <p className={styles.newsHeroCopy}>先看最有时效性的消息，再决定风险暴露和审批优先级。</p>
        </div>
        <div className={styles.newsHeaderActions}>
          <Link to="/events">
            <Button size="sm" variant="primary">事件中心</Button>
          </Link>
          <Link to="/approvals">
            <Button size="sm" variant="outline">审批队列</Button>
          </Link>
          <Link to="/runtime">
            <Button size="sm" variant="outline">运行态</Button>
          </Link>
        </div>
      </header>

      <section
        aria-label="Dashboard 概览"
        className={`${styles.metricsStrip} ${styles.dashboardMetrics}`}
      >
        {dashboardMetrics.map((metric) => (
          <article key={metric.label} className={styles.metricTile}>
            <p className={styles.metricTileLabel}>{metric.label}</p>
            <p className={styles.metricTileValue}>{metric.value}</p>
            <p className={styles.metricTileTrend}>{metric.trend}</p>
          </article>
        ))}
      </section>

      <section className={`${styles.newsFeed} ${styles.dashboardFeed}`}>
        <div className={styles.feedHeader}>
          <div>
            <p className={styles.feedEyebrow}>重点快讯</p>
            <h2 className={styles.feedTitle}>今天最值得先看的三条</h2>
          </div>
          <Link to="/events">
            <Button size="sm" variant="ghost">查看全部</Button>
          </Link>
        </div>
        <div className={styles.feedList}>
          {featuredEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </section>

      <section className={`${styles.sidePanel} ${styles.dashboardWallet}`}>
        <header className={styles.sidePanelHeader}>
          <div>
            <p className={styles.sideEyebrow}>钱包观察</p>
            <h2 className={styles.sideTitle}>亏损与回撤</h2>
          </div>
          <Chip variant="soft" className="w-fit">
            钱包
          </Chip>
        </header>
        <div className={styles.walletMetricGrid}>
          {walletMetrics.map((metric) => (
            <article key={metric.label} className={styles.walletMetricCard}>
              <p className={styles.walletMetricLabel}>{metric.label}</p>
              <p
                className={
                  metric.tone === 'negative'
                    ? styles.walletMetricValueNegative
                    : metric.tone === 'positive'
                      ? styles.walletMetricValuePositive
                      : styles.walletMetricValue
                }
              >
                {metric.value}
              </p>
              <p className={styles.walletMetricDetail}>{metric.detail}</p>
            </article>
          ))}
        </div>
        <WalletPnlChart />
      </section>

      <section className={`${styles.sidePanel} ${styles.dashboardApprovals}`}>
        <header className={styles.sidePanelHeader}>
          <div>
            <p className={styles.sideEyebrow}>审批压力</p>
            <h2 className={styles.sideTitle}>待处理请求</h2>
          </div>
        </header>
        <div className={styles.sideStack}>
          {approvalsQueue.map((approval) => (
            <ApprovalCard key={approval.id} approval={approval} />
          ))}
        </div>
      </section>

      <section className={`${styles.sidePanel} ${styles.dashboardHealth}`}>
        <header className={styles.sidePanelHeader}>
          <div>
            <p className={styles.sideEyebrow}>健康提醒</p>
            <h2 className={styles.sideTitle}>关键异常</h2>
          </div>
        </header>
        <div className={styles.sideStack}>
          {healthAlerts.map((alert) => (
            <HealthCard key={alert.id} alert={alert} />
          ))}
        </div>
      </section>
    </div>
  )
}

export function EventsIndexPageContent() {
  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">事件中心</p>
        <h1 className="page-title">高价值事件</h1>
        <p className="page-description">
          从 Dashboard 进入后的事件浏览和筛选页。这里负责扩展视野，不承担首页总控职责。
        </p>
      </section>

      <section className={styles.sectionGrid}>
        <section className={styles.panel}>
          <SectionHeader
            eyebrow="筛选与排序"
            title="首版只落结构，不发明 API shape"
            description="时间范围、半导体子行业、参考强度、分析状态和来源类型将进入 URL search params；本轮先用静态骨架表达信息架构。"
          />
          <div className={styles.actionRow}>
            <span className={styles.tag}>时间范围</span>
            <span className={styles.tag}>半导体子行业</span>
            <span className={styles.tag}>参考强度</span>
            <span className={styles.tag}>分析状态</span>
            <span className={styles.tag}>最新 + 高价值</span>
          </div>
        </section>

        <section className={styles.panel}>
          <SectionHeader
            eyebrow="系统提醒"
            title="轻量异常摘要"
            description="只做浏览过程中的轻提示，不把运行态排障台塞回事件中心。"
          />
          <div className={styles.list}>
            {healthAlerts.slice(0, 1).map((alert) => (
              <HealthCard key={alert.id} alert={alert} />
            ))}
          </div>
        </section>
      </section>

      <section className={styles.panel}>
        <SectionHeader
          eyebrow="重点事件"
          title="重点事件区与完整列表并存"
          description="重点区解释为什么值得先看，列表承担稳定跳转到事件详情。"
        />
        <div className={styles.list}>
          {featuredEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </section>
    </div>
  )
}

export function EventDetailPageContent({ eventId }: { eventId: string }) {
  const event = featuredEvents.find((item) => item.id === eventId) ?? featuredEvents[0]!

  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">事件详情 / 决策</p>
        <h1 className="page-title">{event.title}</h1>
        <p className="page-description">
          事件事实、行业影响分析和最佳动作建议必须分区展示；本页不直接批准或执行高风险动作。
        </p>
      </section>

      <section className={styles.detailGrid}>
        <section className={styles.panel}>
          <SectionHeader
            eyebrow="事件事实"
            title="左栏先给事实和验证状态"
            description="事实区保留来源、发布时间、事件状态和可信度摘要。"
          />
          <div className={styles.detailSection}>
            <p className={styles.detailText}>来源：{event.source}</p>
            <p className={styles.detailText}>发布时间：{event.publishedAt}</p>
            <p className={styles.detailText}>当前状态：{event.status}</p>
            <p className={styles.detailText}>参考强度：{event.referenceStrength}</p>
            <p className={styles.detailText}>事件概括：{event.summary}</p>
          </div>
          <div className={styles.detailActions}>
            <Link className={styles.secondaryLink} to="/events">
              返回事件中心
            </Link>
            <Link className={styles.secondaryLink} to="/events/$eventId/audit" params={{ eventId: event.id }}>
              审计时间线
            </Link>
          </div>
        </section>

        <section className={styles.panel}>
          <SectionHeader
            eyebrow="行业影响与最佳动作"
            title="右栏首屏优先展示分析和动作"
            description="首版只展示一个最佳动作，不做多候选动作比较工作台。"
          />
          <div className={styles.detailSection}>
            <p className={styles.detailText}>影响行业：{event.industries.join(' / ')}</p>
            <p className={styles.detailText}>影响方向：{event.industryImpact}</p>
            <p className={styles.detailText}>建议动作：{event.actionHint}，等待审批确认后进入受控链路。</p>
            <p className={styles.detailText}>风险摘要：需要 strong_confirm，且当前建议不等于真实执行完成。</p>
          </div>
          <div className={styles.detailActions}>
            <Link className={styles.actionLink} to="/approvals/$approvalId" params={{ approvalId: approvalsQueue[0]!.id }}>
              进入审批
            </Link>
            <Link className={styles.secondaryLink} to="/runtime">
              查看运行摘要
            </Link>
          </div>
        </section>
      </section>

      <section className={styles.sectionGrid}>
        <section className={styles.panel}>
          <SectionHeader
            eyebrow="支持 / 反方观点"
            title="只展示结构化摘要"
            description="不展示完整 chain-of-thought，也不回放原始长推理文本。"
          />
          <ul className={styles.supportList}>
            <li className={styles.timelineItem}>
              <p className={styles.supportListLabel}>支持观点</p>
              <p className={styles.detailText}>出口限制升级直接压缩设备与上游材料板块未来两周风险偏好。</p>
            </li>
            <li className={styles.timelineItem}>
              <p className={styles.supportListLabel}>反方观点</p>
              <p className={styles.detailText}>若后续出现政策缓释或国产替代加速，板块回撤可能快于预期。</p>
            </li>
            <li className={styles.timelineItem}>
              <p className={styles.supportListLabel}>数据缺口</p>
              <p className={styles.detailText}>还缺少二级供应链价格与跨行业对冲信号。</p>
            </li>
          </ul>
        </section>

        <section className={styles.panel}>
          <SectionHeader
            eyebrow="运行摘要"
            title="把 trace / request 入口留给 Runtime"
            description="详情页只给结构化摘要和入口，不替代运行态诊断界面。"
          />
          <div className={styles.detailSection}>
            <p className={styles.detailText}>关联 Agent Run：2</p>
            <p className={styles.detailText}>最近分析状态：decision_ready</p>
            <p className={styles.detailText}>关键工具失败：0</p>
            <p className={styles.detailText}>trace_id 占位：rt-mainflow-evt-001</p>
          </div>
        </section>
      </section>
    </div>
  )
}

export function EventAuditPageContent({ eventId }: { eventId: string }) {
  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">事件级审计</p>
        <h1 className="page-title">事件时间线</h1>
        <p className="page-description">
          按事件回放建议、重分析和人工动作。这里只做时间线骨架，不发明新的审计 contract。
        </p>
      </section>

      <section className={styles.panel}>
        <SectionHeader
          eyebrow="Audit"
          title={`事件 ${eventId} 的关键节点`}
          description="真实审计记录以后端真源为准；本轮先把入口和阅读顺序落地。"
        />
        <div className={styles.timeline}>
          <article className={styles.timelineItem}>
            <p className={styles.supportListLabel}>10:24 · 事件采集</p>
            <p className={styles.detailText}>Source 插件捕获事件并进入路由阶段。</p>
          </article>
          <article className={styles.timelineItem}>
            <p className={styles.supportListLabel}>10:31 · 影响分析完成</p>
            <p className={styles.detailText}>行业影响分析输出结构化摘要并生成最佳动作候选。</p>
          </article>
          <article className={styles.timelineItem}>
            <p className={styles.supportListLabel}>10:36 · 审批请求生成</p>
            <p className={styles.detailText}>高风险建议已进入人工确认链路，等待 strong_confirm。</p>
          </article>
        </div>
      </section>
    </div>
  )
}

export function ApprovalsIndexPageContent() {
  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">人工确认</p>
        <h1 className="page-title">审批工作台</h1>
        <p className="page-description">
          处理 ApprovalRequest 队列。批准只代表人工确认，不代表真实执行完成。
        </p>
      </section>

      <section className={styles.sectionGrid}>
        <section className={styles.panel}>
          <SectionHeader
            eyebrow="队列概览"
            title="高风险、即将过期、强确认请求优先"
            description="本轮先把队列结构、风险标签和详情入口落地。"
          />
          <div className={styles.actionRow}>
            <span className={styles.tag}>pending</span>
            <span className={styles.tag}>approved</span>
            <span className={styles.tag}>rejected</span>
            <span className={styles.tag}>expired</span>
            <span className={styles.tag}>increase_risk</span>
          </div>
        </section>

        <section className={styles.panel}>
          <SectionHeader
            eyebrow="批量处理边界"
            title="默认更保守"
            description="manual_only、即将自动过期和确认等级不一致的请求不进入首版批量处理。"
          />
          <div className={styles.emptyState}>
            <h2 className={styles.sectionTitle}>受限批量操作</h2>
            <p className={styles.emptyCopy}>本轮只表达边界，不提供真实批量 approve 按钮。</p>
          </div>
        </section>
      </section>

      <section className={styles.panel}>
        <SectionHeader
          eyebrow="审批列表"
          title="每条审批都要能看懂风险和到期策略"
          description="详情页负责完整上下文，列表页负责优先级、风险方向和入口。"
        />
        <div className={styles.list}>
          {approvalsQueue.map((approval) => (
            <ApprovalCard key={approval.id} approval={approval} />
          ))}
        </div>
      </section>
    </div>
  )
}

export function ApprovalDetailPageContent({ approvalId }: { approvalId: string }) {
  const approval = approvalsQueue.find((item) => item.id === approvalId) ?? approvalsQueue[0]!

  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">审批详情</p>
        <h1 className="page-title">{approval.actionLabel}</h1>
        <p className="page-description">
          单条审批的完整上下文页。这里展示确认等级、到期策略和动作边界，但不把批准写成已下单。
        </p>
      </section>

      <section className={styles.detailGrid}>
        <section className={styles.panel}>
          <SectionHeader
            eyebrow="审批上下文"
            title="事件、建议与风险方向"
            description="首版先落结构化摘要和动作入口，不接真实 mutation。"
          />
          <div className={styles.detailSection}>
            <p className={styles.detailText}>关联事件：{approval.eventTitle}</p>
            <p className={styles.detailText}>推荐度：{approval.recommendation}</p>
            <p className={styles.detailText}>风险方向：{approval.riskDirection}</p>
            <p className={styles.detailText}>风险等级：{approval.riskLevel}</p>
            <p className={styles.detailText}>确认等级：{approval.confirmationLevel}</p>
            <p className={styles.detailText}>剩余时间：{approval.expiresIn}</p>
          </div>
        </section>

        <section className={styles.panel}>
          <SectionHeader
            eyebrow="动作区"
            title="动作类型先收口，不伪造成功状态"
            description="approve / reject / request_reanalysis / amend 作为正式动作类型保留，但本轮只做结构和解释。"
          />
          <div className={styles.actionRow}>
            <span className={styles.tag}>approve</span>
            <span className={styles.tag}>reject</span>
            <span className={styles.tag}>request_reanalysis</span>
            <span className={styles.tag}>amend</span>
          </div>
          <p className={styles.detailText}>
            若动作失败，后续真实实现必须展示 request_id / trace_id。本轮仅保留展示位，不发明后端响应。
          </p>
          <div className={styles.detailActions}>
            <Link className={styles.secondaryLink} to="/events/$eventId" params={{ eventId: featuredEvents[0]!.id }}>
              查看关联事件
            </Link>
            <Link className={styles.secondaryLink} to="/approval-link/$token" params={{ token: 'preview-token' }}>
              预览授权页
            </Link>
          </div>
        </section>
      </section>
    </div>
  )
}

export function ApprovalLinkPageContent({ token }: { token: string }) {
  return (
    <div className={styles.page}>
      <section className="page-header">
        <p className="page-kicker">一次性授权</p>
        <h1 className="page-title">Approval Link</h1>
        <p className="page-description">
          独立于后台壳之外的受限确认入口。token 校验和短期上下文以后端真源为准。
        </p>
      </section>

      <section className={styles.panel}>
        <SectionHeader
          eyebrow="Link Confirm"
          title="受限入口只表达语义，不绕过强确认"
          description="manual_only 不能通过一次性链接绕过；首版保留受限上下文、风险提示和返回审批工作台入口。"
        />
        <div className={styles.detailSection}>
          <p className={styles.detailText}>token 占位：{token}</p>
          <p className={styles.detailText}>确认等级：link_confirm</p>
          <p className={styles.detailText}>状态：等待后端校验并换取短期上下文</p>
        </div>
        <div className={styles.detailActions}>
          <Link className={styles.secondaryLink} to="/approvals">
            返回审批工作台
          </Link>
        </div>
      </section>
    </div>
  )
}

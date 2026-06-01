import { Button } from '@heroui/react'
import { useState } from 'react'

import { runtimeAgentRuns } from '../mock-data'
import { PageSectionCard } from '../components/PageSectionCard'
import { SectionHeader } from '../components/SectionHeader'
import { maskToken } from '../utils/format'
import { ApprovalScoreCard } from '@/features/event-scoring/components/ApprovalScoreCard'
import {
  scoredApprovals,
  scoredEvents,
} from '@/features/event-scoring/mocks/event-scoring.mock'
import { formatRecommendationPriority } from '@/features/event-scoring/utils/event-scoring-labels'
import { LinkButton } from '@/shared/ui'
import { DetailFacts, InfoTag, PageHeader } from './shared'

export function ApprovalsIndexPageContent() {
  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="人工确认"
        title="审批工作台"
        description="处理 ApprovalRequest 队列。批准只代表人工确认，不代表真实执行完成。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="队列概览"
            title="待处理、即将过期、高风险与强确认优先"
            description="列表页需要让用户在首屏就理解风险方向、确认等级、到期策略和建议内容。"
          />
          <div className="flex flex-wrap gap-2">
            {['pending', 'approved', 'rejected', 'expired', 'increase_risk', 'strong_confirm', 'manual_only'].map((item) => (
              <InfoTag key={item}>{item}</InfoTag>
            ))}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="批量处理边界"
            title="批量操作必须比逐条处理更保守"
            description="manual_only、确认等级不一致和即将进入自动过期处理的请求不进入首版批量处理。"
          />
          <div className="grid min-h-[180px] place-items-center gap-2 rounded-lg border border-dashed border-hairline-strong bg-surface p-5 text-center">
            <h2 className="m-0 text-title-md font-bold text-ink">受限批量操作</h2>
            <p className="m-0 text-body-sm text-muted">本轮只表达边界，不提供真实批量 approve 按钮。</p>
          </div>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="审批列表"
          title="每条审批都要能看懂风险和到期策略"
          description="详情页负责完整上下文，列表页负责优先级、风险方向、确认等级和入口。"
        />
        <div className="grid gap-3">
          {scoredApprovals.map((approval) => (
            <ApprovalScoreCard key={approval.id} approval={approval} />
          ))}
        </div>
      </PageSectionCard>
    </div>
  )
}

export function ApprovalDetailPageContent({ approvalId }: { approvalId: string }) {
  const approval = scoredApprovals.find((item) => item.id === approvalId)

  if (!approval) {
    return (
      <div className="grid gap-5">
        <PageHeader
          kicker="审批详情"
          title="审批不存在"
          description="当前审批 ID 没有匹配到 mock 数据，请返回审批工作台重新选择。"
        />
        <PageSectionCard>
          <SectionHeader
            eyebrow="未找到"
            title="当前审批已移除或 ID 无效"
            description="首版 mock 页面不做静默兜底到其他审批，避免误导操盘者查看了错误上下文。"
          />
          <div className="flex flex-wrap gap-2">
            <LinkButton to="/approvals" variant="outline">
              返回审批工作台
            </LinkButton>
          </div>
        </PageSectionCard>
      </div>
    )
  }

  const relatedEvent = scoredEvents.find((item) => item.id === approval.eventId) ?? null
  const relatedRun = runtimeAgentRuns.find((item) => item.eventId === approval.eventId) ?? null

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="审批详情"
        title={approval.actionLabel}
        description="单条审批的完整上下文页。这里展示确认等级、到期策略和动作边界，但不把批准写成已下单。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="审批上下文"
            title="事件、建议、风险方向和证据摘要"
            description="审批详情要回答 ActionRequest 为什么产生，以及 Policy Gate 要求怎样的人类确认。"
          />
          <DetailFacts
            rows={[
              `Approval ID：${approval.id}`,
              `关联事件：${approval.eventTitle}`,
              `推荐优先级：${formatRecommendationPriority(approval.scoreContext.recommendationPriority)}`,
              `建议推荐度：${approval.scoreContext.recommendationScore} / 100`,
              `事件可信度摘要：${approval.scoreContext.eventReliabilitySummary} / 100`,
              `分析置信度摘要：${approval.scoreContext.analysisConfidenceSummary} / 100`,
              `风险方向：${approval.scoreContext.riskDirection}`,
              `风险等级：${approval.scoreContext.riskLevel}`,
              `确认等级：${approval.scoreContext.confirmationLevel}`,
              `剩余时间：${approval.scoreContext.expiresIn}`,
              `到期策略：${approval.scoreContext.expirationAction}`,
              `事件来源：${relatedEvent?.source ?? '待补充'}`,
              `阻断 / 降级：${approval.degradationNotices.map((item) => item.title).join(' / ') || '当前无阻断或降级提示'}`,
              `触发摘要：${approval.triggerSummary}`,
            ]}
          />
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="动作区"
            title="动作类型先收口，不伪造成功状态"
            description="approve / reject / request_reanalysis / amend 作为正式动作类型保留，但本轮只做结构和解释。"
          />
          <div className="flex flex-wrap gap-2">
            {['approve', 'reject', 'request_reanalysis', 'amend'].map((item) => (
              <InfoTag key={item}>{item}</InfoTag>
            ))}
          </div>
          <p className="m-0 text-body-sm text-muted">
            increase_risk 默认二次确认；manual_only 不能通过弱确认入口处理。真实动作失败时必须展示 request_id / trace_id。
          </p>
          <div className="flex flex-wrap gap-2">
            {relatedEvent ? (
              <LinkButton to="/events/$eventId" params={{ eventId: relatedEvent.id }} variant="outline">
                查看关联事件
              </LinkButton>
            ) : (
              <InfoTag>当前审批暂无关联事件</InfoTag>
            )}
            {relatedRun ? (
              <LinkButton to="/runtime/agents/$runId" params={{ runId: relatedRun.id }} variant="outline">
                查看运行详情
              </LinkButton>
            ) : null}
            <LinkButton to="/approval-link/$token" params={{ token: 'preview-token' }} variant="outline">
              预览授权页
            </LinkButton>
          </div>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="处理历史"
          title="保留人工动作和修改前后摘要"
          description="处理历史和审计记录是审批详情的一部分，但不在这里发明真正的后端审计 shape。"
        />
        <div className="grid gap-3">
          {[
            ['审批创建', '系统根据高风险建议生成 ApprovalRequest，并写入到期策略。'],
            ['等待确认', '当前请求处于待处理状态，等待 strong_confirm / manual_only 入口。'],
            ['后续动作', 'approve、reject、request_reanalysis、amend 的真实审计以后端真源为准。'],
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

export function ApprovalLinkPageContent({ token }: { token: string }) {
  const [showFullToken, setShowFullToken] = useState(false)

  async function handleCopyToken() {
    await navigator.clipboard.writeText(token)
  }

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="一次性授权"
        title="Approval Link"
        description="独立于后台壳之外的受限确认入口。token 校验和短期上下文以后端真源为准。"
      />

      <PageSectionCard>
        <SectionHeader
          eyebrow="Link Confirm"
          title="受限入口只表达语义，不绕过强确认"
          description="manual_only 不能通过一次性链接绕过；首版保留受限上下文、风险提示和返回审批工作台入口。"
        />
        <DetailFacts
          rows={[
            `token 占位：${showFullToken ? token : maskToken(token)}`,
            '确认等级：link_confirm',
            '状态：等待后端校验并换取短期上下文',
            '风险边界：不允许在一次性链接页绕过高风险强确认规则',
          ]}
        />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onPress={() => setShowFullToken((value) => !value)}>
            {showFullToken ? '隐藏完整值' : '显示完整值'}
          </Button>
          <Button size="sm" variant="outline" onPress={() => void handleCopyToken()}>
            复制完整值
          </Button>
          <LinkButton to="/approvals" variant="outline">
            返回审批工作台
          </LinkButton>
        </div>
      </PageSectionCard>
    </div>
  )
}

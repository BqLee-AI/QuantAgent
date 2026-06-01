import {
  Card,
  Chip,
} from '@heroui/react'

import { LinkButton } from '@/shared/ui'

import type { ApprovalScoreCardModel } from '../types/event-scoring.types'
import { DegradationNoticeList } from './DegradationNoticeList'
import { formatRecommendationPriority } from '../utils/event-scoring-labels'

export function ApprovalScoreCard({ approval }: { approval: ApprovalScoreCardModel }) {
  return (
    <Card className="border border-hairline bg-surface-soft/80">
      <div className="flex flex-wrap gap-2 p-4 pb-0">
        <Chip size="sm" variant="soft">{approval.scoreContext.riskDirection}</Chip>
        <Chip size="sm" variant="soft">{approval.scoreContext.riskLevel}</Chip>
        <Chip size="sm" variant="soft">{approval.scoreContext.confirmationLevel}</Chip>
      </div>
      <div className="grid gap-2 p-4">
        <h3 className="m-0 text-title-sm font-bold text-ink">{approval.actionLabel}</h3>
        <p className="m-0 text-body-sm text-muted">
          {approval.eventTitle}
        </p>
        <p className="m-0 text-body-sm text-muted">
          {formatRecommendationPriority(approval.scoreContext.recommendationPriority)}
          {' · '}
          推荐度 {approval.scoreContext.recommendationScore} / 100
          {' · '}
          可信度 {approval.scoreContext.eventReliabilitySummary} / 100
        </p>
        <p className="m-0 text-body-sm text-muted">
          分析置信度 {approval.scoreContext.analysisConfidenceSummary} / 100 · {approval.scoreContext.expiresIn}
        </p>
        <p className="m-0 text-body-sm text-muted">
          到期策略：{approval.scoreContext.expirationAction}
        </p>
        <p className="m-0 text-body-sm text-muted">
          {approval.triggerSummary}
        </p>
        <DegradationNoticeList notices={approval.degradationNotices} />
      </div>
      <div className="flex flex-wrap gap-2 p-4 pt-0">
        <LinkButton to="/approvals/$approvalId" params={{ approvalId: approval.id }}>
          查看审批
        </LinkButton>
        <LinkButton to="/events/$eventId" params={{ eventId: approval.eventId }} variant="outline">
          查看关联事件
        </LinkButton>
      </div>
    </Card>
  )
}

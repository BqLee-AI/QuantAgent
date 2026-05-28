import {
  Card,
  Chip,
} from '@heroui/react'

import type { ApprovalSummary } from '../mock-data'
import { LinkButton } from './LinkButton'

export function ApprovalCard({ approval }: { approval: ApprovalSummary }) {
  return (
    <Card className="border border-hairline bg-surface-soft/80">
      <div className="flex flex-wrap gap-2 p-4 pb-0">
        <Chip size="sm" variant="soft">{approval.riskDirection}</Chip>
        <Chip size="sm" variant="soft">{approval.riskLevel}</Chip>
        <Chip size="sm" variant="soft">{approval.confirmationLevel}</Chip>
      </div>
      <div className="grid gap-2 p-4">
        <h3 className="m-0 text-title-sm font-bold text-ink">{approval.actionLabel}</h3>
        <p className="m-0 text-body-sm text-muted">
          {approval.eventTitle} · {approval.recommendation} · {approval.expiresIn}
        </p>
      </div>
      <div className="flex flex-wrap gap-2 p-4 pt-0">
        <LinkButton to="/approvals/$approvalId" params={{ approvalId: approval.id }}>
          查看审批
        </LinkButton>
        <LinkButton to="/approvals" variant="outline">
          回到审批队列
        </LinkButton>
      </div>
    </Card>
  )
}

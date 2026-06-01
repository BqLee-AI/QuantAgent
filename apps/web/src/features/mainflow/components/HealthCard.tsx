import {
  Card,
  Chip,
} from '@heroui/react'

import type { HealthAlert } from '../mock-data'
import { LinkButton } from '@/shared/ui'

export function HealthCard({ alert }: { alert: HealthAlert }) {
  return (
    <Card className="border border-hairline bg-surface-soft/80">
      <div className="p-4 pb-0">
        <Chip size="sm" variant="soft">{alert.severity}</Chip>
      </div>
      <div className="grid gap-2 p-4">
        <h3 className="m-0 text-title-sm font-bold text-ink">{alert.title}</h3>
        <p className="m-0 text-body-sm text-muted">{alert.summary}</p>
        <p className="m-0 text-body-sm text-muted">{alert.traceHint}</p>
      </div>
      <div className="flex flex-wrap gap-2 p-4 pt-0">
        {alert.relatedRunId ? (
          <LinkButton to="/runtime/agents/$runId" params={{ runId: alert.relatedRunId }}>
            查看关联运行
          </LinkButton>
        ) : null}
        <LinkButton to="/runtime" variant="outline">
          进入运行态
        </LinkButton>
      </div>
    </Card>
  )
}

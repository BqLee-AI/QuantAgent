import {
  Card,
  Chip,
} from '@heroui/react'
import { twMerge } from 'tailwind-merge'

import { LinkButton } from '@/shared/ui'
import { formatRelativeMinutes } from '@/shared/utils'

import type { EventScoreCardModel } from '../types/event-scoring.types'
import {
  formatEventReliability,
  formatFreshnessLabel,
  formatImpactStrength,
  formatPriorityLabel,
} from '../utils/event-scoring-labels'

const summaryCardClass = 'h-full border border-hairline bg-surface'
const accentChipClass = 'bg-surface-soft text-body-sm font-bold text-ink'
const subtleChipClass = 'bg-surface-soft text-body-sm font-bold text-muted-strong'

export function DashboardEventSummaryCard({ event }: { event: EventScoreCardModel }) {
  return (
    <Card className={summaryCardClass}>
      <div className="grid gap-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Chip className={twMerge(accentChipClass)} size="sm" variant="soft">
            {formatPriorityLabel(event.score.eventPriority, event.score.priorityBand)}
          </Chip>
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatEventReliability(event.score.eventReliability)}
          </Chip>
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatImpactStrength(event.score.impactStrength)}
          </Chip>
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatFreshnessLabel(event.score.freshness)}
          </Chip>
        </div>

        <div className="grid gap-1.5">
          <h3 className="m-0 wrap-anywhere text-title-sm font-bold text-ink">
            {event.title}
          </h3>
          <p className="m-0 text-body-sm font-bold text-muted">
            {formatRelativeMinutes(event.publishedMinutesAgo)} · {event.source}
          </p>
        </div>

        <p className="m-0 text-body-sm leading-[1.55] text-body">
          {event.summary}
        </p>

        <div className="grid gap-2">
          <p className="m-0 text-body-sm leading-[1.5] text-muted-strong">
            入选原因：{event.score.selectionReason}
          </p>
          <p className="m-0 text-body-sm leading-[1.5] text-muted-strong">
            {event.actionHint}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <LinkButton to="/events/$eventId" params={{ eventId: event.id }}>
            查看分析
          </LinkButton>
          <LinkButton to="/events" variant="outline">
            查看全部
          </LinkButton>
        </div>
      </div>
    </Card>
  )
}

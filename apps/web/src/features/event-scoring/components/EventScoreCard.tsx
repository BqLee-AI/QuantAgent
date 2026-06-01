import {
  Card,
  Chip,
} from '@heroui/react'
import { twMerge } from 'tailwind-merge'

import { LinkButton } from '@/shared/ui'
import { formatRelativeMinutes } from '@/shared/utils'

import type { EventScoreCardModel } from '../types/event-scoring.types'
import { DegradationNoticeList } from './DegradationNoticeList'
import {
  formatEventReliability,
  formatFreshnessLabel,
  formatImpactStrength,
  formatPriorityLabel,
  formatSourceAuthority,
  formatVerificationStatus,
} from '../utils/event-scoring-labels'

const eventCardClass = 'h-full border border-hairline bg-surface'
const primaryChipClass = 'bg-surface-soft text-body-sm font-bold text-ink'
const subtleChipClass = 'bg-surface-soft text-body-sm font-bold text-muted-strong'
const dangerChipClass = 'bg-danger/10 text-body-sm font-bold text-danger'

export function EventScoreCard({
  event,
  toDetail = true,
}: {
  event: EventScoreCardModel
  toDetail?: boolean
}) {
  return (
    <Card className={eventCardClass}>
      <div className="flex flex-col items-start gap-3 p-4 pb-0">
        <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className={twMerge(primaryChipClass)} size="sm" variant="soft">
              {formatPriorityLabel(event.score.eventPriority, event.score.priorityBand)}
            </Chip>
            <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
              {formatEventReliability(event.score.eventReliability)}
            </Chip>
            <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
              {formatFreshnessLabel(event.score.freshness)}
            </Chip>
          </div>
          <Chip className={twMerge(dangerChipClass)} size="sm" variant="soft">
            {event.impactDirection}
          </Chip>
        </div>
        <div className="grid gap-1.5">
          <h3 className="m-0 wrap-anywhere text-title-sm font-bold text-ink">
            {event.title}
          </h3>
          <p className="m-0 text-body-sm font-bold text-muted">
            {formatRelativeMinutes(event.publishedMinutesAgo)} · {event.source} · {event.sourceType}
          </p>
        </div>
      </div>

      <div className="grid gap-4 p-4">
        <div className="flex flex-wrap gap-2">
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatSourceAuthority(event.score.sourceAuthority)}
          </Chip>
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatImpactStrength(event.score.impactStrength)}
          </Chip>
          <Chip className={twMerge(subtleChipClass)} size="sm" variant="soft">
            {formatVerificationStatus(event.score.verificationStatus)}
          </Chip>
        </div>

        <p className="m-0 min-h-[calc(1.55em*4)] text-body-sm leading-[1.55] text-body">
          {event.summary}
        </p>

        <div className="grid gap-3">
          <DegradationNoticeList notices={event.degradationNotices} />
          <div className="flex flex-wrap gap-2">
            {event.industries.map((industry) => (
              <Chip
                key={industry}
                className={twMerge(subtleChipClass)}
                size="sm"
                variant="soft"
              >
                {industry}
              </Chip>
            ))}
          </div>
          <p className="m-0 text-body-sm leading-[1.5] text-muted-strong">
            入选原因：{event.score.selectionReason}
          </p>
          <p className="m-0 text-body-sm leading-[1.5] text-muted-strong">
            {event.actionHint}
          </p>
        </div>
      </div>

      {toDetail ? (
        <div className="flex flex-wrap gap-2 p-4 pt-0">
          <LinkButton to="/events/$eventId" params={{ eventId: event.id }}>
            查看分析
          </LinkButton>
          <LinkButton to="/events/$eventId/audit" params={{ eventId: event.id }} variant="outline">
            审计时间线
          </LinkButton>
        </div>
      ) : null}
    </Card>
  )
}

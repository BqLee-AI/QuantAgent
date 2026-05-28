import {
  Card,
  Chip,
} from '@heroui/react'

import type { EventSummary } from '../mock-data'
import { formatRelativeMinutes } from '../utils/format'
import { LinkButton } from './LinkButton'

export function EventCard({
  event,
  toDetail = true,
}: {
  event: EventSummary
  toDetail?: boolean
}) {
  return (
    <Card className="h-full border border-hairline bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))]">
      <div className="flex flex-col items-start gap-3 p-4 pb-0">
        <div className="flex w-full flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className="bg-[rgb(59_130_246_/_0.12)] text-[10px] font-bold text-[rgb(29_78_216)]" size="sm" variant="soft">
              {event.priority}
            </Chip>
            <Chip className="bg-[rgb(15_23_42_/_0.06)] text-[10px] font-bold text-muted-strong" size="sm" variant="soft">
              参考强度 {event.referenceStrength}
            </Chip>
            <Chip className="bg-[rgb(15_23_42_/_0.06)] text-[10px] font-bold text-muted-strong" size="sm" variant="soft">
              状态 {event.status}
            </Chip>
          </div>
          <Chip className="bg-[rgb(220_38_38_/_0.1)] text-[10px] font-bold text-[rgb(153_27_27)]" size="sm" variant="soft">
            {event.industryImpact}
          </Chip>
        </div>
        <div className="grid gap-1.5">
          <h3 className="m-0 overflow-wrap-anywhere text-title-sm font-bold text-ink">
            {event.title}
          </h3>
          <p className="m-0 text-[11px] font-bold text-muted">
            {formatRelativeMinutes(event.publishedMinutesAgo)} · {event.source}
          </p>
        </div>
      </div>

      <div className="grid gap-4 p-4">
        <p className="m-0 min-h-[calc(1.55em*4)] text-body-sm leading-[1.55] text-body">
          {event.summary}
        </p>
        <div className="grid gap-3">
          <div className="flex flex-wrap gap-2">
            {event.industries.map((industry) => (
              <Chip
                key={industry}
                className="bg-[rgb(148_163_184_/_0.12)] text-[10px] font-bold text-[rgb(51_65_85)]"
                size="sm"
                variant="soft"
              >
                {industry}
              </Chip>
            ))}
          </div>
          <p className="m-0 text-[11px] leading-[1.5] text-muted-strong">
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

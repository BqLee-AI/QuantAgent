import { Chip } from '@heroui/react'
import { twMerge } from 'tailwind-merge'

import type { EventDegradationNotice } from '../types/event-scoring.types'
import { formatDegradationTone } from '../utils/event-scoring-labels'

function getToneClass(tone: ReturnType<typeof formatDegradationTone>) {
  switch (tone) {
    case 'danger':
      return 'bg-danger/10 text-danger'
    case 'warning':
      return 'bg-warning/10 text-warning'
    case 'muted':
      return 'bg-surface-soft text-muted'
    case 'neutral':
    default:
      return 'bg-surface-soft text-muted-strong'
  }
}

export function DegradationNoticeList({
  notices,
}: {
  notices: readonly EventDegradationNotice[]
}) {
  if (notices.length === 0) {
    return null
  }

  return (
    <div className="grid gap-2 rounded-lg border border-dashed border-hairline-strong bg-surface-soft/70 p-3">
      {notices.map((notice, index) => {
        const tone = formatDegradationTone(notice.kind)

        return (
          <div key={`${notice.kind}-${notice.title}-${notice.traceId ?? notice.requestId ?? index}`} className="grid gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <Chip className={twMerge('text-body-sm font-bold', getToneClass(tone))} size="sm" variant="soft">
                {notice.title}
              </Chip>
              {notice.traceId ? (
                <span className="text-body-sm font-bold text-muted">
                  trace_id: {notice.traceId}
                </span>
              ) : null}
              {notice.requestId ? (
                <span className="text-body-sm font-bold text-muted">
                  request_id: {notice.requestId}
                </span>
              ) : null}
            </div>
            <p className="m-0 text-body-sm leading-[1.5] text-muted-strong">
              {notice.summary}
            </p>
          </div>
        )
      })}
    </div>
  )
}

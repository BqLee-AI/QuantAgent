import type { EventScoreCardModel } from '../types/event-scoring.types'

export function selectDashboardHighlightedEvents(events: readonly EventScoreCardModel[]) {
  return events
    .filter((event) => {
      if (event.status === 'analysis_failed' || event.status === 'policy_blocked') {
        return false
      }

      if (event.degradationNotices.some((notice) => notice.kind === 'stale_event' || notice.kind === 'invalid_analysis')) {
        return false
      }

      return event.score.eventPriority >= 65
    })
    .sort((left, right) => right.score.eventPriority - left.score.eventPriority)
    .slice(0, 3)
}

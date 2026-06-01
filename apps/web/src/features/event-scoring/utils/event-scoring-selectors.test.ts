import {
  describe,
  expect,
  it,
} from 'vitest'

import { scoredEvents } from '../mocks/event-scoring.mock'
import { selectDashboardHighlightedEvents } from './event-scoring-selectors'

describe('event scoring selectors', () => {
  it('filters out stale, invalid, and policy-blocked events from dashboard highlights', () => {
    const highlighted = selectDashboardHighlightedEvents(scoredEvents)

    expect(highlighted.map((event) => event.id)).toEqual([
      'evt-semiconductor-export',
      'evt-semiconductor-memory',
      'evt-semiconductor-foundry',
    ])
  })

  it('returns the top three events by event priority after filtering', () => {
    const reordered = [
      scoredEvents[2]!,
      scoredEvents[1]!,
      scoredEvents[0]!,
    ]

    const highlighted = selectDashboardHighlightedEvents(reordered)

    expect(highlighted.map((event) => event.id)).toEqual([
      'evt-semiconductor-export',
      'evt-semiconductor-memory',
      'evt-semiconductor-foundry',
    ])
  })
})

import {
  describe,
  expect,
  it,
} from 'vitest'

import { healthAlerts } from '@/features/mainflow/mock-data'

import { scoredEvents } from '../mocks/event-scoring.mock'
import { createHealthAlertEventCardModel } from './event-scoring-adapters'

describe('event scoring adapters', () => {
  it('maps a health alert into a non-ranking event card model', () => {
    const event = createHealthAlertEventCardModel(healthAlerts[0]!, scoredEvents[0]!)

    expect(event.id).toBe(healthAlerts[0]!.id)
    expect(event.source).toBe('系统健康')
    expect(event.degradationNotices).toEqual([])
    expect(event.score.eventPriority).toBe(40)
    expect(event.score.selectionReason).toContain('不参与高价值事件打分')
  })
})

import { toApiError } from '@/shared/api'
import {
  scoredApprovals,
  scoredEvents,
} from '@/features/event-scoring/mocks/event-scoring.mock'
import { runtimeAgentRuns } from '@/features/mainflow/mock-data'

import {
  createEmptyEventAuditTimeline,
  createUnavailableEventAuditTimeline,
  eventAuditMockTimelines,
} from '../mocks/event-audit.mock'
import { useEventAuditTimeline } from '../queries'
import type { EventAuditPageModel } from '../types'
import { sortEventAuditNodes } from '../utils'

export function useEventAuditPage(eventId: string) {
  const event = scoredEvents.find((item) => item.id === eventId) ?? null
  const relatedApproval = event ? scoredApprovals.find((item) => item.eventId === event.id) ?? null : null
  const relatedRun = event ? runtimeAgentRuns.find((item) => item.eventId === event.id) ?? null : null
  const query = useEventAuditTimeline(eventId, { enabled: event !== null })
  const queryError = query.error ? toApiError(query.error) : null

  const fallbackTimeline = eventAuditMockTimelines[eventId] ?? (event ? createEmptyEventAuditTimeline(eventId) : createUnavailableEventAuditTimeline(eventId))
  const forbiddenTimeline = {
    availability: {
      message: '当前账号无权查看事件审计详情。',
      state: 'forbidden' as const,
    },
    eventId,
    nodes: [],
  }
  const useFallback = !query.data || queryError !== null
  const timeline = queryError?.status === 403 ? forbiddenTimeline : useFallback ? fallbackTimeline : query.data
  const pageModel: EventAuditPageModel = {
    availability: queryError
      ? queryError.status === 403
        ? {
            message: `当前账号无权查看事件审计详情。${queryError.requestId ? ` Request ID: ${queryError.requestId}` : ''}`,
            state: 'forbidden',
          }
        : {
            message: `后端事件审计接口读取失败，当前展示结构化占位数据。${queryError.requestId ? ` Request ID: ${queryError.requestId}` : ''}`,
            state: timeline.availability.state,
          }
      : timeline.availability,
    eventId,
    nodes: sortEventAuditNodes(timeline.nodes),
    source: queryError?.status === 403 ? 'api' : useFallback ? 'mock-fallback' : 'api',
  }

  // 中文注释：后端事件审计 contract 尚未接通时，页面只能展示明确标识的占位数据，不能冒充真实审计。
  return {
    event,
    isLoading: query.isLoading && !query.data,
    pageModel,
    queryError,
    refetch: query.refetch,
    relatedApproval,
    relatedRun,
  }
}

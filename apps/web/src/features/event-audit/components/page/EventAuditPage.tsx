import { useMemo, useState } from 'react'

import { formatVerificationStatus } from '@/features/event-scoring/utils/event-scoring-labels'
import {
  PageHeader,
  SectionHeader,
} from '@/shared/ui'

import { useEventAuditPage } from '../../hooks'
import type { EventAuditNodeFilter } from '../../types'
import { filterEventAuditNodes } from '../../utils'
import { EventAuditNodeFilterPicker } from '../filters/EventAuditNodeFilterPicker'
import { EventAuditNotFoundState } from '../states/EventAuditStatePanel'
import { EventAuditInsightPanel } from '../summary/EventAuditInsightPanel'
import { EventAuditTimeline } from '../timeline/EventAuditTimeline'

export function EventAuditPage({ eventId }: { eventId: string }) {
  const [nodeFilter, setNodeFilter] = useState<EventAuditNodeFilter>('all')
  const {
    event,
    isLoading,
    pageModel,
    queryError,
    refetch,
    relatedApproval,
    relatedRun,
  } = useEventAuditPage(eventId)

  if (!event) {
    return <EventAuditNotFoundState />
  }

  const filteredNodes = useMemo(
    () => filterEventAuditNodes(pageModel.nodes, nodeFilter),
    [nodeFilter, pageModel.nodes],
  )

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件级审计"
        title={event.title}
      />

      <EventAuditInsightPanel
        eventReliability={event.score.eventReliability}
        eventId={event.id}
        eventTitle={event.title}
        isLoading={isLoading}
        nodes={pageModel.nodes}
        onRetry={queryError ? () => void refetch() : undefined}
        relatedApprovalId={relatedApproval?.id}
        relatedRunId={relatedRun?.id}
        requestId={queryError?.requestId}
        source={pageModel.source}
        statusMessage={pageModel.availability.message}
        traceId={queryError?.traceId}
        verificationLabel={formatVerificationStatus(event.score.verificationStatus)}
      />

      <section className="grid gap-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <SectionHeader eyebrow="关键节点" />
          <EventAuditNodeFilterPicker value={nodeFilter} onChange={setNodeFilter} />
        </div>
        <EventAuditTimeline emptyMessage={pageModel.availability.message} nodes={filteredNodes} />
      </section>
    </div>
  )
}

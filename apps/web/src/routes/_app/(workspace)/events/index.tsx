import { createFileRoute } from '@tanstack/react-router'

import { PageEmpty } from '../../../../app/components/PageEmpty'
import { PageLoading } from '../../../../app/components/PageLoading'
import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'
import styles from '../../../events/index.module.css'

type EventsPreviewState = 'loading' | 'empty'

type EventsSearch = {
  state?: EventsPreviewState
}

export const Route = createFileRoute('/_app/(workspace)/events/')({
  validateSearch: (search): EventsSearch => ({
    state: isEventsPreviewState(search.state) ? search.state : undefined,
  }),
  component: EventsPage,
})

function EventsPage() {
  const { state } = Route.useSearch()

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">事件中心</p>
        <h1 className="page-title">事件</h1>
        <p className="page-description">
          查看来源事件、处理状态和相关运行轨迹，作为事件分发与复核的统一工作台。
        </p>
      </section>

      {state === 'loading' ? <PageLoading message="正在加载事件工作台..." /> : null}

      {state === 'empty' ? (
        <PageEmpty
          title="当前没有可处理事件"
          description="这个预览状态下还没有可供查看的来源事件。"
          cta={
            <button className={styles.previewAction} type="button">
              预览操作
            </button>
          }
        />
      ) : null}

      {!state ? (
        <section className="placeholder-grid" aria-label="事件总览">
          <PlaceholderPanel title="待接入" copy="已采集但尚未完成路由和分析的事件。" />
          <PlaceholderPanel title="处理中" copy="已关联 Agent run、插件任务或人工处理流程的事件。" />
          <PlaceholderPanel title="已完成" copy="已经形成决策、审计记录或审批结果的事件。" />
        </section>
      ) : null}
    </>
  )
}

function isEventsPreviewState(value: unknown): value is EventsPreviewState {
  return value === 'loading' || value === 'empty'
}

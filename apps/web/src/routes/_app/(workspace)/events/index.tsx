import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'
import styles from '../../../events/index.module.css'

export const Route = createFileRoute('/_app/(workspace)/events/')({
  component: EventsPage,
})

function EventsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">事件中心</p>
        <h1 className="page-title">事件</h1>
        <p className="page-description">
          查看来源事件、处理状态和相关运行轨迹，作为事件分发与复核的统一工作台。
        </p>
      </section>

      <section className={styles.overviewGrid} aria-label="事件总览">
        <PlaceholderPanel title="待接入" copy="已采集但尚未完成路由和分析的事件。" />
        <PlaceholderPanel title="处理中" copy="已关联 Agent run、插件任务或人工处理流程的事件。" />
        <PlaceholderPanel title="已完成" copy="已经形成决策、审计记录或审批结果的事件。" />
      </section>
    </>
  )
}

import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/runtime/')({
  component: RuntimePage,
})

function RuntimePage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">运行态</p>
        <h1 className="page-title">运行看板</h1>
        <p className="page-description">
          统一查看 Agent 运行、工具调用、调度活动和系统健康状态。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="运行态总览">
        <PlaceholderPanel title="Agent 运行" copy="最近运行、状态变化和关联追踪信息。" />
        <PlaceholderPanel title="工具调用" copy="调用状态、重试次数、耗时和错误摘要。" />
        <PlaceholderPanel title="调度任务" copy="排队任务、完成任务和运行失败情况。" />
      </section>
    </>
  )
}

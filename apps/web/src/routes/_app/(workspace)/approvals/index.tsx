import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/approvals/')({
  component: ApprovalsPage,
})

function ApprovalsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">人工确认</p>
        <h1 className="page-title">审批队列</h1>
        <p className="page-description">
          处理待确认、即将超时、已处理和自动执行后的人工授权请求。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="审批总览">
        <PlaceholderPanel title="待处理" copy="等待批准、拒绝、重分析或补充修改的请求。" />
        <PlaceholderPanel title="即将超时" copy="需要在策略时限前优先处理的短窗口审批。" />
        <PlaceholderPanel title="已处理" copy="已批准、已拒绝、已过期或执行后通知的记录。" />
      </section>
    </>
  )
}

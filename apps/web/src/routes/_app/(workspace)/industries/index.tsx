import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/industries/')({
  component: IndustriesPage,
})

function IndustriesPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">行业包</p>
        <h1 className="page-title">行业模块</h1>
        <p className="page-description">
          查看行业模块的边界、市场覆盖和来源绑定关系。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="行业模块总览">
        <PlaceholderPanel title="模块" copy="梳理行业包职责和领域边界。" />
        <PlaceholderPanel title="市场覆盖" copy="查看已覆盖市场和来源绑定信息。" />
        <PlaceholderPanel title="依赖状态" copy="关注模块准备度和依赖健康情况。" />
      </section>
    </>
  )
}

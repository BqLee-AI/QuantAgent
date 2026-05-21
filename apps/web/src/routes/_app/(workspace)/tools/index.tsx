import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/tools/')({
  component: ToolsPage,
})

function ToolsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">工具</p>
        <h1 className="page-title">工具注册表</h1>
        <p className="page-description">
          查看工具 schema、运行可用性和来源归属，作为工具治理入口。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="工具总览">
        <PlaceholderPanel title="Schema" copy="汇总工具定义、输入输出和约束信息。" />
        <PlaceholderPanel title="可用性" copy="检查运行健康状态和兼容性信号。" />
        <PlaceholderPanel title="来源" copy="展示平台或插件侧的归属关系。" />
      </section>
    </>
  )
}

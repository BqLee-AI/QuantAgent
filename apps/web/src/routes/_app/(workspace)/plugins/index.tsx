import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/plugins/')({
  component: PluginsPage,
})

function PluginsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">插件</p>
        <h1 className="page-title">插件管理</h1>
        <p className="page-description">
          管理来源、行业、策略、通知和执行器等插件的安装、配置与运行状态。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="插件总览">
        <PlaceholderPanel title="已安装" copy="查看已注册插件的类型、版本和健康状态。" />
        <PlaceholderPanel title="配置" copy="管理基于 schema 的设置、密钥引用和校验结果。" />
        <PlaceholderPanel title="运维操作" copy="执行启用、停用、重载和故障排查。" />
      </section>
    </>
  )
}

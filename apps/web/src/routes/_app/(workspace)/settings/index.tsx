import { createFileRoute } from '@tanstack/react-router'

import { PlaceholderPanel } from '../../../../app/components/PlaceholderPanel'

export const Route = createFileRoute('/_app/(workspace)/settings/')({
  component: SettingsPage,
})

function SettingsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">设置</p>
        <h1 className="page-title">系统设置</h1>
        <p className="page-description">
          管理本地认证、通知通道、密钥引用、授权策略和实时状态配置。
        </p>
      </section>

      <section className="placeholder-grid" aria-label="系统设置总览">
        <PlaceholderPanel title="访问控制" copy="查看会话配置和能力可见性。" />
        <PlaceholderPanel title="通知" copy="管理告警通道配置和投递健康状态。" />
        <PlaceholderPanel title="密钥引用" copy="查看受策略保护的密钥引用和管理入口。" />
      </section>
    </>
  )
}

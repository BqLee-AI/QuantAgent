import { useRuntimeConfig } from '../../../shared/config'
import { useAuth } from '../../../shared/auth'
import { PageSectionCard } from '../components/PageSectionCard'
import { SectionHeader } from '../components/SectionHeader'
import { DetailFacts, InfoTag, PageHeader } from './shared'

export function SettingsPageContent() {
  const auth = useAuth()
  const runtimeConfig = useRuntimeConfig()
  const capabilities = Array.from(auth.capabilities).sort()

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Settings"
        title="个人偏好与会话设置"
        description="Settings 只承接会话、个人偏好和前端体验偏好，不承接插件配置、模型策略或生产风控规则。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="会话与身份"
            title="身份、环境和 capability 摘要"
            description="这里只说明当前身份与前端可见环境，不展示 token 或 secret 原文。"
          />
          <DetailFacts
            rows={[
              `actor：${auth.actor?.actor_id ?? '未登录'}`,
              `actor_type：${auth.actor?.actor_type ?? 'unknown'}`,
              `环境：${runtimeConfig.mode}`,
              `鉴权：${runtimeConfig.authEnabled ? '已开启' : '已关闭'}`,
              `登录状态：${auth.status}`,
            ]}
          />
          <div className="flex flex-wrap gap-2">
            {capabilities.length > 0 ? capabilities.map((item) => <InfoTag key={item}>{item}</InfoTag>) : <InfoTag>暂无 capability</InfoTag>}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="通知提醒偏好"
            title="只影响前端提醒体验"
            description="外部通知渠道配置属于 notification 插件治理，不在 Settings 中管理。"
          />
          <DetailFacts
            rows={[
              'UI 内提醒：默认开启',
              '声音提醒：默认关闭',
              '即将过期审批提醒：默认开启',
              '高风险审批提醒：默认开启',
            ]}
          />
        </PageSectionCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="实时连接和刷新"
            title="只改展示体验，不改状态真源原则"
            description="这些偏好不能改变 REST 作为状态真源，也不能绕过后端权限校验。"
          />
          <DetailFacts
            rows={[
              '是否显示断连提醒：是',
              '当前页面自动刷新间隔：30 秒',
              '重连后自动刷新当前页面：是',
            ]}
          />
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="展示偏好"
            title="只影响展示，不影响策略行为"
            description="高风险系统能力都应进入更强权限和审计的治理入口。"
          />
          <DetailFacts
            rows={[
              '默认时间范围：今日',
              '默认列表密度：标准',
              '是否高亮 increase_risk：是',
              '是否默认折叠运行摘要：否',
            ]}
          />
        </PageSectionCard>
      </section>
    </div>
  )
}

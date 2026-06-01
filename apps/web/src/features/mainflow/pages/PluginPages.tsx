import { Button } from '@heroui/react'

import { PlaceholderPanel } from '../../../app/components/PlaceholderPanel'
import { LinkButton } from '../components/LinkButton'
import { PageSectionCard } from '../components/PageSectionCard'
import { SectionHeader } from '../components/SectionHeader'
import { pluginRecords } from '../mock-data'
import { DetailFacts, InfoTag, PageHeader } from './shared'

export function PluginsIndexPageContent() {
  const typeTabs = ['All', 'Sources', 'Industries', 'Strategies', 'Notifications', 'Brokers'] as const

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Registry / Plugins"
        title="插件治理"
        description="统一管理 source、industry、strategy、notification、broker 五类插件，不再把 Skill、Tool、Industry Package 平铺成顶层导航。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.9fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="类型视图"
            title="按插件类型治理，而不是按技术子对象平铺"
            description="Industry 插件内部可以提供 Skill / Tool / MarketMapping，但这些对象不再成为顶层页面。"
          />
          <div className="flex flex-wrap gap-2">
            {typeTabs.map((item) => (
              <InfoTag key={item}>{item}</InfoTag>
            ))}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="关键边界"
            title="Broker 仍然只支持 disabled / dry_run / mock"
            description="列表页只提供筛选、查看详情和低风险入口；高风险操作进入 Plugin Detail。"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <PlaceholderPanel title="依赖阻塞" copy="聚焦 dependency_missing、config_invalid、installed_but_blocked 等阻塞原因。" />
            <PlaceholderPanel title="Broker 边界" copy="明确初版不支持真实执行配置中心，只展示 dry_run / mock 能力。" />
          </div>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="插件列表"
          title="一个入口理解插件总体状态"
          description="每条插件都能进入详情，继续查看配置、依赖、能力、健康和审计。"
        />
        <div className="grid gap-3">
          {pluginRecords.map((plugin) => (
            <article key={plugin.id} className="grid gap-3 rounded-lg border border-hairline bg-surface-soft p-4">
              <div className="flex flex-wrap gap-2">
                <InfoTag>{plugin.type}</InfoTag>
                <InfoTag>{plugin.status}</InfoTag>
                <InfoTag>{plugin.source}</InfoTag>
              </div>
              <div className="grid gap-1">
                <h3 className="m-0 text-title-sm font-bold text-ink">{plugin.name}</h3>
                <p className="m-0 text-body-sm text-muted">
                  plugin_id: {plugin.id} · installed_version: {plugin.version}
                </p>
                <p className="m-0 text-body-sm text-muted">{plugin.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <LinkButton to="/plugins/$pluginId" params={{ pluginId: plugin.id }}>
                  查看插件详情
                </LinkButton>
                {plugin.relatedEventId ? (
                  <LinkButton to="/events/$eventId" params={{ eventId: plugin.relatedEventId }} variant="outline">
                    查看关联事件
                  </LinkButton>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </PageSectionCard>
    </div>
  )
}

export function PluginDetailPageContent({ pluginId }: { pluginId: string }) {
  const plugin = pluginRecords.find((item) => item.id === pluginId) ?? pluginRecords[0]!
  const tabs = ['Overview', 'Config', 'Dependencies', 'Provided Capabilities', 'Health', 'Audit', 'Ops'] as const

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Plugin Detail"
        title={plugin.name}
        description="不同类型插件共享同一详情页骨架，tab 内容按插件类型变化。Skill 和 Tool 只作为插件提供能力展示。"
      />

      <PageSectionCard>
        <SectionHeader
          eyebrow="详情骨架"
          title="配置、依赖、能力、健康、审计与运维动作"
          description="首版占位先把阅读骨架和跳转关系落地，不发明后端字段。"
        />
        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => (
            <InfoTag key={item}>{item}</InfoTag>
          ))}
        </div>
      </PageSectionCard>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="Overview"
            title="先判断插件为什么可用或不可用"
            description="阻塞原因要能区分来自配置、依赖、权限还是运行错误。"
          />
          <DetailFacts
            rows={[
              `plugin_id：${plugin.id}`,
              `type：${plugin.type}`,
              `source：${plugin.source}`,
              `installed_version：${plugin.version}`,
              `status：${plugin.status}`,
              `blocked_reason：${plugin.blockedReason}`,
              `last_error：${plugin.lastError}`,
            ]}
          />
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="Provided Capabilities"
            title="按插件类型展示能力层级"
            description="Industry 插件重点展示 SourceBinding、AgentDefinition、Skill、Tool 和 MarketMapping 摘要。"
          />
          <DetailFacts rows={plugin.capabilities} />
        </PageSectionCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="Config / Dependencies"
            title="配置保存必须带 validate 和审计语义"
            description="敏感字段只显示 masked value 或 secret reference，不允许插件注入自定义前端组件。"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <PlaceholderPanel title="Schema-driven Config" copy="保存前先 validate；保存后创建配置快照并写审计。" />
            <PlaceholderPanel title="Dependencies" copy="区分 plugin / python / system dependencies，并给出 reverse dependencies 语义。" />
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="Health / Ops"
            title="高风险动作必须二次确认"
            description="broker 类型要明确只支持 disabled / dry_run / mock，不能暗示真实执行已上线。"
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" type="button" variant="outline">enable</Button>
            <Button size="sm" type="button" variant="outline">disable</Button>
            <Button size="sm" type="button" variant="outline">reload</Button>
          </div>
          <p className="m-0 text-body-sm text-muted">
            这里只做动作占位和边界说明，不伪造真实操作成功状态。
          </p>
          <div className="flex flex-wrap gap-2">
            <LinkButton to="/plugins" variant="outline">
              返回插件列表
            </LinkButton>
            <LinkButton to="/runtime" variant="outline">
              查看运行排障
            </LinkButton>
          </div>
        </PageSectionCard>
      </section>
    </div>
  )
}

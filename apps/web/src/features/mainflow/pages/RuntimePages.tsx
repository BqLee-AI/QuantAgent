import { LinkButton } from '../components/LinkButton'
import { PageSectionCard } from '../components/PageSectionCard'
import { SectionHeader } from '../components/SectionHeader'
import {
  runtimeAgentRuns,
  runtimeErrors,
  runtimeFilters,
  runtimeHealthSummary,
  runtimeToolInvocations,
} from '../mock-data'
import { DetailFacts, InfoTag, PageHeader } from './shared'

export function RuntimeDashboardPageContent() {
  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Runtime"
        title="运行态"
        description="用于解释系统为什么这样判断，以及当前运行过程是否影响判断质量。这里不是操盘首页。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.95fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="运行健康摘要"
            title="先看运行健康，再看具体失败"
            description="首版占位按 AgentRun、ToolInvocation、RuntimeError 三条主线组织，不退化成日志墙。"
          />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {runtimeHealthSummary.map((item) => (
              <article key={item.label} className="grid gap-1.5 rounded-lg border border-hairline bg-surface-soft p-3">
                <p className="m-0 text-[12px] font-bold text-muted">{item.label}</p>
                <p className="m-0 text-[22px] font-bold text-ink">{item.value}</p>
                <p className="m-0 text-body-sm text-muted">{item.description}</p>
              </article>
            ))}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="筛选与追踪"
            title="围绕 event_id / trace_id 排查"
            description="真实筛选条件以后端 contract 为准。本轮先保证筛选位和追踪入口完整。"
          />
          <div className="flex flex-wrap gap-2">
            {runtimeFilters.map((item) => (
              <InfoTag key={item}>{item}</InfoTag>
            ))}
          </div>
          <p className="m-0 text-body-sm text-muted">
            运行页支持从事件详情、审计时间线和插件详情回跳，不要求用户手输 ID。
          </p>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="AgentRun"
          title="运行过程摘要"
          description="展示 provider_policy、model_used、耗时和错误摘要，并提供详情入口。"
        />
        <div className="grid gap-3">
          {runtimeAgentRuns.map((run) => (
            <article key={run.id} className="grid gap-3 rounded-lg border border-hairline bg-surface-soft p-4">
              <div className="flex flex-wrap gap-2">
                <InfoTag>{run.status}</InfoTag>
                <InfoTag>{run.runType}</InfoTag>
                <InfoTag>{run.providerPolicy}</InfoTag>
              </div>
              <div className="grid gap-1">
                <h3 className="m-0 text-title-sm font-bold text-ink">{run.id}</h3>
                <p className="m-0 text-body-sm text-muted">
                  event_id: {run.eventId} · model: {run.modelUsed} · duration: {run.duration}
                </p>
                <p className="m-0 text-body-sm text-muted">{run.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <LinkButton to="/runtime/agents/$runId" params={{ runId: run.id }}>
                  查看 Agent Run
                </LinkButton>
                <LinkButton to="/events/$eventId" params={{ eventId: run.eventId }} variant="outline">
                  查看关联事件
                </LinkButton>
              </div>
            </article>
          ))}
        </div>
      </PageSectionCard>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="ToolInvocation"
            title="工具调用摘要"
            description="只展示受控工具调用的结构化摘要，不展示敏感原始输入输出。"
          />
          <div className="grid gap-3">
            {runtimeToolInvocations.map((item) => (
              <article key={item.id} className="grid gap-3 rounded-lg border border-hairline bg-surface-soft p-4">
                <div className="flex flex-wrap gap-2">
                  <InfoTag>{item.status}</InfoTag>
                  <InfoTag>{item.riskLevel}</InfoTag>
                  {item.requiresHumanApproval ? <InfoTag>requires_human_approval</InfoTag> : null}
                </div>
                <div className="grid gap-1">
                  <h3 className="m-0 text-title-sm font-bold text-ink">{item.toolName}</h3>
                  <p className="m-0 text-body-sm text-muted">
                    invocation_id: {item.id} · provider_plugin_id: {item.pluginId}
                  </p>
                  <p className="m-0 text-body-sm text-muted">{item.summary}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <LinkButton to="/runtime/tools/$invocationId" params={{ invocationId: item.id }}>
                    查看工具调用
                  </LinkButton>
                  <LinkButton to="/plugins/$pluginId" params={{ pluginId: item.pluginId }} variant="outline">
                    查看来源插件
                  </LinkButton>
                </div>
              </article>
            ))}
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="RuntimeError"
            title="关键失败摘要"
            description="严重错误要可见，但不替代日志平台。这里只保留排障主线和关联入口。"
          />
          <div className="grid gap-3">
            {runtimeErrors.map((item) => (
              <article key={item.id} className="grid gap-2 rounded-lg border border-hairline bg-surface-soft p-4">
                <div className="flex flex-wrap gap-2">
                  <InfoTag>{item.severity}</InfoTag>
                  <InfoTag>{item.component}</InfoTag>
                  {item.providerPolicy ? <InfoTag>{item.providerPolicy}</InfoTag> : null}
                </div>
                <p className="m-0 text-title-sm font-bold text-ink">{item.title}</p>
                <p className="m-0 text-body-sm text-muted">{item.summary}</p>
                <p className="m-0 text-body-sm text-muted">
                  trace_id: {item.traceId}
                  {item.eventId ? ` · event_id: ${item.eventId}` : ''}
                  {item.pluginId ? ` · plugin_id: ${item.pluginId}` : ''}
                </p>
                <div className="flex flex-wrap gap-2">
                  {item.eventId ? (
                    <LinkButton to="/events/$eventId" params={{ eventId: item.eventId }} variant="outline">
                      查看关联事件
                    </LinkButton>
                  ) : null}
                  {item.pluginId ? (
                    <LinkButton to="/plugins/$pluginId" params={{ pluginId: item.pluginId }} variant="outline">
                      查看关联插件
                    </LinkButton>
                  ) : null}
                  {item.providerPolicy ? (
                    <LinkButton to="/models" variant="outline">
                      查看模型治理
                    </LinkButton>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </PageSectionCard>
      </section>
    </div>
  )
}

export function RuntimeAgentRunDetailPageContent({ runId }: { runId: string }) {
  const run = runtimeAgentRuns.find((item) => item.id === runId) ?? runtimeAgentRuns[0]!
  const relatedTools = runtimeToolInvocations.filter((item) => item.agentRunId === run.id)

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Agent Run 详情"
        title={run.id}
        description="展示一次 AgentRuntime 运行的结构化过程摘要，不展示完整推理链或完整 provider 原始响应。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="Run 摘要"
            title="状态、输入输出与模型治理入口"
            description="用于回答这次分析跑了什么、用了哪个 policy、哪里失败。"
          />
          <DetailFacts
            rows={[
              `run_id：${run.id}`,
              `event_id：${run.eventId}`,
              `run_type：${run.runType}`,
              `status：${run.status}`,
              `provider_policy：${run.providerPolicy}`,
              `model_used：${run.modelUsed}`,
              `token_usage：${run.tokenUsage}`,
              `cost_estimate：${run.costEstimate}`,
              `trace_id：${run.traceId}`,
            ]}
          />
          <div className="flex flex-wrap gap-2">
            <LinkButton to="/events/$eventId" params={{ eventId: run.eventId }} variant="outline">
              查看事件详情
            </LinkButton>
            <LinkButton to="/models" variant="outline">
              查看模型治理
            </LinkButton>
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="Timeline"
            title="结构化步骤摘要"
            description="只展示 Router、Agent、Tool、schema validation 等结构化步骤，不展示完整 chain-of-thought。"
          />
          <div className="grid gap-3">
            {run.timeline.map((step) => (
              <article key={step.title} className="grid gap-1.5 border-l-2 border-hairline-strong pl-3.5">
                <p className="m-0 text-[12px] font-bold text-muted">{step.title}</p>
                <p className="m-0 text-body-sm text-muted">{step.copy}</p>
              </article>
            ))}
          </div>
        </PageSectionCard>
      </section>

      <PageSectionCard>
        <SectionHeader
          eyebrow="Tools"
          title="关联工具调用"
          description="Tool 详情页承接更细的受控输入输出和阻断原因。"
        />
        <div className="grid gap-3">
          {relatedTools.map((item) => (
            <article key={item.id} className="grid gap-2 rounded-lg border border-hairline bg-surface-soft p-4">
              <div className="flex flex-wrap gap-2">
                <InfoTag>{item.status}</InfoTag>
                <InfoTag>{item.toolName}</InfoTag>
              </div>
              <p className="m-0 text-body-sm text-muted">{item.summary}</p>
              <div className="flex flex-wrap gap-2">
                <LinkButton to="/runtime/tools/$invocationId" params={{ invocationId: item.id }}>
                  查看 Tool Invocation
                </LinkButton>
                <LinkButton to="/plugins/$pluginId" params={{ pluginId: item.pluginId }} variant="outline">
                  查看来源插件
                </LinkButton>
              </div>
            </article>
          ))}
        </div>
      </PageSectionCard>
    </div>
  )
}

export function RuntimeToolInvocationDetailPageContent({ invocationId }: { invocationId: string }) {
  const item =
    runtimeToolInvocations.find((entry) => entry.id === invocationId) ?? runtimeToolInvocations[0]!

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="Tool Invocation 详情"
        title={item.toolName}
        description="用于查看一次受控工具调用的摘要、风险、阻断原因和 trace，不是自由脚本执行器。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
        <PageSectionCard>
          <SectionHeader
            eyebrow="调用摘要"
            title="状态、权限与脱敏输入输出"
            description="完整 payload 和敏感参数不在这里展示，只保留结构化摘要。"
          />
          <DetailFacts
            rows={[
              `invocation_id：${item.id}`,
              `agent_run_id：${item.agentRunId}`,
              `event_id：${item.eventId}`,
              `tool_id：${item.toolId}`,
              `risk_level：${item.riskLevel}`,
              `status：${item.status}`,
              `timeout_ms：${item.timeoutMs}`,
              `retry_count：${item.retryCount}`,
              `duration：${item.duration}`,
              `trace_id：${item.traceId}`,
            ]}
          />
          <div className="flex flex-wrap gap-2">
            <LinkButton to="/runtime/agents/$runId" params={{ runId: item.agentRunId }} variant="outline">
              查看 Agent Run
            </LinkButton>
            <LinkButton to="/plugins/$pluginId" params={{ pluginId: item.pluginId }} variant="outline">
              查看来源插件
            </LinkButton>
          </div>
        </PageSectionCard>

        <PageSectionCard>
          <SectionHeader
            eyebrow="阻断与输出"
            title="关注权限、风险和错误摘要"
            description="失败、超时或 blocked 都要可解释，但不外泄 secret 或完整网页快照。"
          />
          <DetailFacts
            rows={[
              `requires_human_approval：${item.requiresHumanApproval ? '是' : '否'}`,
              `input_summary：${item.inputSummary}`,
              `output_summary：${item.outputSummary}`,
              `error_summary：${item.errorSummary}`,
              `request_id：${item.requestId}`,
            ]}
          />
        </PageSectionCard>
      </section>
    </div>
  )
}

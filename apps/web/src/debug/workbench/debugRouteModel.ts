import type {
  DebugPageRouteDefinition,
  DebugPageRouteKey,
  DebugPageState,
  DebugRoutePreview,
} from './debugRouteTypes'

export const debugPageStateOptions: DebugPageState[] = ['overview', 'loading', 'empty', 'empty-cta']

export const debugPageRoutes: DebugPageRouteDefinition[] = [
  {
    key: 'events',
    label: '事件',
    kicker: '事件中心',
    title: '高价值事件中心',
    description:
      '用于查看重点事件、筛选结果和稳定进入事件详情 / 审计页的事件浏览工作台。',
    loadingMessage: '正在加载事件工作台...',
    emptyTitle: '当前没有可处理事件',
    emptyDescription: '这个预览状态下还没有可供查看的来源事件。',
    overview: [
      { title: '重点事件', copy: '解释今天为什么优先看这些事件。' },
      { title: '筛选与排序', copy: '按时间、行业、可信度和分析状态收窄范围。' },
      { title: '事件列表', copy: '承接稳定进入事件详情和审计时间线。' },
    ],
    ctaLabel: '预览操作',
  },
  {
    key: 'runtime',
    label: '运行态',
    kicker: 'Runtime',
    title: '运行态',
    description:
      '用于查看 AgentRun、ToolInvocation 和 RuntimeError 的解释与排障页。',
    loadingMessage: '正在加载运行时工作台...',
    emptyTitle: '当前没有运行时活动',
    emptyDescription:
      '这个预览状态下还没有 AgentRun、ToolInvocation 或 RuntimeError 可供展示。',
    overview: [
      { title: '运行健康摘要', copy: '先看运行健康，再看具体失败。' },
      { title: 'Agent Runs', copy: '最近运行记录、模型 policy 和 trace 引用。' },
      { title: '工具调用与错误', copy: '调用状态、风险等级、阻断原因和错误摘要。' },
    ],
  },
  {
    key: 'approvals',
    label: '审批',
    kicker: '审批工作台',
    title: '审批工作台',
    description:
      '用于处理待审批、即将过期、已处理和已过期审批请求的人工确认队列。',
    loadingMessage: '正在加载审批工作台...',
    emptyTitle: '当前没有待处理审批',
    emptyDescription:
      '这个预览状态下还没有待处理、即将过期或已处理的审批请求可供展示。',
    overview: [
      { title: '队列概览', copy: '优先看高风险、即将过期和强确认请求。' },
      { title: '审批列表', copy: '逐条理解风险方向、确认等级和到期策略。' },
      { title: '受限批量边界', copy: '批量处理必须比逐条处理更保守。' },
    ],
  },
  {
    key: 'plugins',
    label: '插件',
    kicker: 'Registry / Plugins',
    title: '插件治理',
    description:
      '统一管理 source、industry、strategy、notification、broker 五类插件。',
    loadingMessage: '正在加载插件清单...',
    emptyTitle: '当前没有可用插件',
    emptyDescription:
      '这个预览状态下还没有已安装集成或配置记录可供展示。',
    overview: [
      { title: '类型视图', copy: '按插件类型治理，而不是平铺 Skill / Tool / Industry。' },
      { title: '插件列表', copy: '查看类型、版本、健康状态和详情入口。' },
      { title: '关键阻塞', copy: '关注依赖、配置、权限和 broker 边界。' },
    ],
    ctaLabel: '预览安装流程',
  },
  {
    key: 'models',
    label: '模型',
    kicker: 'Model Providers / LLM Policies',
    title: '模型治理',
    description:
      '用于查看模型供应商、provider policy、fallback、预算、失败和调用成本摘要。',
    loadingMessage: '正在加载模型治理页...',
    emptyTitle: '当前没有已配置模型供应商',
    emptyDescription:
      '这个预览状态下还没有 provider、policy 或调用记录可供展示。',
    overview: [
      { title: 'Provider 列表', copy: '找对象并快速看状态。' },
      { title: 'Provider 详情', copy: '编辑连接配置、模型管理和状态。' },
      { title: 'Policy / Usage', copy: '查看固定 policy、失败摘要和成本治理信息。' },
    ],
  },
  {
    key: 'settings',
    label: '设置',
    kicker: '设置',
    title: '个人偏好与会话设置',
    description:
      '只承接会话、个人偏好和前端体验偏好，不承接 secret 管理或高风险系统规则。',
    loadingMessage: '正在加载设置工作台...',
    emptyTitle: '当前没有已配置设置',
    emptyDescription:
      '这个预览状态下还没有会话快照或个人偏好可供展示。',
    overview: [
      { title: '会话与身份', copy: '查看 actor、环境和 capability 摘要。' },
      { title: '通知提醒偏好', copy: '只影响前端提醒体验。' },
      { title: '展示与刷新偏好', copy: '不改变 REST 状态真源原则。' },
    ],
    ctaLabel: '预览设置操作',
  },
]

export function isDebugPageRouteKey(value: unknown): value is DebugPageRouteKey {
  return debugPageRoutes.some((route) => route.key === value)
}

export function isDebugPageState(value: unknown): value is DebugPageState {
  return debugPageStateOptions.includes(value as DebugPageState)
}

export function isDebugRoutePreview(value: unknown): value is DebugRoutePreview {
  return value === 'loading' || value === 'empty'
}

export function getDebugPageRoute(route: DebugPageRouteKey | undefined): DebugPageRouteDefinition {
  return debugPageRoutes.find((entry) => entry.key === route) ?? debugPageRoutes[0]
}

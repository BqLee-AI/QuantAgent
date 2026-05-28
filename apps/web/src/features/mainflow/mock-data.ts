export interface DashboardMetric {
  label: string
  value: string
  trend: string
}

export interface EventSummary {
  id: string
  title: string
  source: string
  publishedAt: string
  publishedMinutesAgo: number
  priority: string
  referenceStrength: string
  industryImpact: string
  status: string
  summary: string
  actionHint: string
  industries: string[]
}

export interface ApprovalSummary {
  id: string
  eventTitle: string
  actionLabel: string
  recommendation: string
  riskDirection: string
  riskLevel: string
  expiresIn: string
  confirmationLevel: string
}

export interface HealthAlert {
  id: string
  title: string
  severity: string
  summary: string
  traceHint: string
}

export interface WalletMetric {
  label: string
  value: string
  tone: 'negative' | 'neutral' | 'positive'
  detail: string
}

export interface WalletBarDatum {
  day: string
  pnl: number
}

export const dashboardMetrics: readonly DashboardMetric[] = [
  { label: '今日半导体事件', value: '05', trend: '较昨日 +2' },
  { label: '待处理审批', value: '03', trend: '1 条将在 20 分钟内过期' },
  { label: '关键健康提醒', value: '02', trend: '1 条影响事件分析成功率' },
  { label: '钱包回撤关注', value: '04', trend: '2 个仓位处于日内亏损区间' },
]

export const featuredEvents: readonly EventSummary[] = [
  {
    id: 'evt-semiconductor-export',
    title: '北美半导体出口限制升级，设备链预期再下修',
    source: '全球财经快讯',
    publishedAt: '2026-05-28 10:24',
    publishedMinutesAgo: 96,
    priority: 'P0',
    referenceStrength: '高',
    industryImpact: '半导体设备偏空',
    status: 'decision_ready',
    summary:
      '出口限制进一步收紧后，设备、材料与成熟制程链条的订单兑现预期同步转弱，市场正在重新计价未来两个季度的资本开支与替代节奏，设备链短线波动和估值回撤压力明显抬升。',
    actionHint: '优先复核设备链仓位暴露与替代率假设',
    industries: ['半导体设备', '上游材料'],
  },
  {
    id: 'evt-semiconductor-memory',
    title: '存储厂启动新一轮报价试探，NAND 现货价格继续抬升',
    source: '渠道报价监测',
    publishedAt: '2026-05-28 09:12',
    publishedMinutesAgo: 168,
    priority: 'P1',
    referenceStrength: '中高',
    industryImpact: '存储链偏多',
    status: 'analyzing',
    summary:
      '现货价格继续试探上沿，若报价在未来 2 到 3 个交易日仍能维持抬升，同时下游接单与渠道补库节奏没有转弱，存储链景气修复的可信度会明显增强，板块弹性也会被进一步放大。',
    actionHint: '观察报价持续性与下游接单反馈是否同步改善',
    industries: ['存储芯片', '封测'],
  },
  {
    id: 'evt-semiconductor-foundry',
    title: '晶圆代工厂传出下季成熟制程议价松动，功率器件链承压',
    source: '产业链跟踪',
    publishedAt: '2026-05-28 08:47',
    publishedMinutesAgo: 193,
    priority: 'P1',
    referenceStrength: '中',
    industryImpact: '成熟制程偏空',
    status: 'pending_approval',
    summary:
      '功率器件与 MCU 所在的成熟制程供需仍偏松，若下季议价继续松动，相关公司的毛利率修复时间点可能再次后移，市场对盈利预测的下修压力会先体现在功率半导体和代工弹性标的上。',
    actionHint: '检查成熟制程敞口和盈利下修敏感度',
    industries: ['晶圆代工', '功率半导体'],
  },
]

export const approvalsQueue: readonly ApprovalSummary[] = [
  {
    id: 'apr-semiconductor-01',
    eventTitle: '北美半导体出口限制升级，设备链预期再下修',
    actionLabel: '降低半导体设备板块风险暴露',
    recommendation: '高优先级',
    riskDirection: 'increase_risk',
    riskLevel: '高',
    expiresIn: '18 分钟',
    confirmationLevel: 'strong_confirm',
  },
  {
    id: 'apr-memory-02',
    eventTitle: '存储厂启动新一轮报价试探，NAND 现货价格继续抬升',
    actionLabel: '请求重分析并补充库存去化验证',
    recommendation: '复核优先',
    riskDirection: 'neutral',
    riskLevel: '中',
    expiresIn: '45 分钟',
    confirmationLevel: 'manual_only',
  },
  {
    id: 'apr-foundry-03',
    eventTitle: '晶圆代工厂传出下季成熟制程议价松动，功率器件链承压',
    actionLabel: '维持减仓建议并等待二次确认',
    recommendation: '中优先级',
    riskDirection: 'reduce_risk',
    riskLevel: '中',
    expiresIn: '2 小时',
    confirmationLevel: 'link_confirm',
  },
]

export const healthAlerts: readonly HealthAlert[] = [
  {
    id: 'health-source-1',
    title: '半导体资讯 source 插件连续失败',
    severity: '高',
    summary: '过去 20 分钟内 3 次抓取失败，可能影响事件覆盖完整度。',
    traceHint: 'trace_id: rt-source-412',
  },
  {
    id: 'health-tool-2',
    title: '行业影响分析工具超时率升高',
    severity: '中',
    summary: '最近 10 次分析中 2 次超过 SLA，建议检查 provider fallback。',
    traceHint: 'trace_id: tool-impact-98',
  },
]

export const walletMetrics: readonly WalletMetric[] = [
  {
    label: '账户净值',
    value: '¥ 2,486,300',
    tone: 'neutral',
    detail: '较昨日收盘 -1.8%',
  },
  {
    label: '当日盈亏',
    value: '-¥ 43,200',
    tone: 'negative',
    detail: '亏损主要集中在设备链与功率半导体',
  },
  {
    label: '本周最大回撤',
    value: '-3.9%',
    tone: 'negative',
    detail: '周二午后开始扩大，尚未修复到安全区',
  },
]

export const walletTrend: readonly WalletBarDatum[] = [
  { day: 'Mon', pnl: 18_000 },
  { day: 'Tue', pnl: -24_000 },
  { day: 'Wed', pnl: -39_000 },
  { day: 'Thu', pnl: 12_000 },
  { day: 'Fri', pnl: -43_200 },
]

import type { EventAuditTimelineResponse } from '../api'

export const eventAuditMockTimelines: Record<string, EventAuditTimelineResponse> = {
  'evt-semiconductor-export': {
    availability: {
      message: '后端事件审计接口未接通，当前展示结构化占位数据。',
      state: 'degraded',
    },
    eventId: 'evt-semiconductor-export',
    nodes: [
      {
        action: 'captured',
        actor: { id: 'source.global-news', label: 'Source 插件', type: 'system' },
        kind: 'event.state_changed',
        occurredAt: '2026-05-28T10:24:00+08:00',
        outcome: 'captured -> routed',
        requestId: 'req-capture-102',
        summary: '主流媒体事件被采集并进入半导体行业路由。',
        traceId: 'trace-export-102',
      },
      {
        action: 'analysis_completed',
        actor: { id: 'industry.semiconductor', label: '半导体行业包', type: 'system' },
        kind: 'industry.analysis.completed',
        occurredAt: '2026-05-28T10:31:00+08:00',
        outcome: 'analysis completed',
        runId: 'run-semiconductor-export-01',
        summary: '行业影响分析输出设备链偏空、材料链承压的结构化摘要。',
        traceId: 'trace-export-102',
      },
      {
        action: 'decision_created',
        actor: { id: 'decision.engine', label: 'Decision Engine', type: 'system' },
        kind: 'decision.created',
        occurredAt: '2026-05-28T10:35:00+08:00',
        outcome: 'recommendation created',
        summary: '生成降低半导体设备板块风险暴露的首版建议。',
        suggestionChange: {
          after: {
            confidence: 76,
            recommendationScore: 79,
            summary: '降低半导体设备板块风险暴露。',
          },
          before: {
            confidence: 0,
            recommendationScore: 0,
            summary: '事件刚完成路由，尚未形成建议。',
          },
          reason: '高可信事件与设备链影响强度同时升高。',
          scoreDelta: 79,
        },
        traceId: 'trace-export-102',
      },
      {
        action: 'approval_requested',
        actor: { id: 'policy.gate', label: 'Policy Gate', type: 'system' },
        approvalId: 'apr-semiconductor-01',
        kind: 'approval.requested',
        occurredAt: '2026-05-28T10:36:00+08:00',
        outcome: 'strong_confirm required',
        summary: '高风险建议进入人工确认链路，等待 strong_confirm。',
        traceId: 'trace-export-102',
      },
      {
        action: 'request_reanalysis',
        actor: { id: 'operator.lead', label: '操盘负责人', type: 'human' },
        approvalId: 'apr-semiconductor-01',
        kind: 'reanalysis.requested',
        occurredAt: '2026-05-28T10:42:00+08:00',
        outcome: 'reanalysis queued',
        runId: 'run-semiconductor-export-02',
        summary: '因工具超时要求补充验证国产替代反馈，再判断是否维持建议。',
        traceId: 'trace-export-102',
      },
      {
        action: 'decision_changed',
        actor: { id: 'decision.engine', label: 'Decision Engine', type: 'system' },
        kind: 'decision.changed',
        occurredAt: '2026-05-28T10:49:00+08:00',
        outcome: 'recommendation updated',
        runId: 'run-semiconductor-export-02',
        summary: '重分析后维持降低风险暴露建议，但把置信度从 72 调整为 76。',
        suggestionChange: {
          after: {
            confidence: 76,
            recommendationScore: 79,
            summary: '维持降低半导体设备板块风险暴露，等待人工确认。',
          },
          before: {
            confidence: 72,
            recommendationScore: 74,
            summary: '降低半导体设备板块风险暴露，但国产替代反馈未验证。',
          },
          reason: '补充验证未发现足以抵消出口限制影响的缓释信号。',
          scoreDelta: 5,
        },
        traceId: 'trace-export-102',
      },
    ],
  },
  'evt-semiconductor-memory': {
    availability: {
      message: '后端事件审计接口未接通，当前展示结构化占位数据。',
      state: 'degraded',
    },
    eventId: 'evt-semiconductor-memory',
    nodes: [
      {
        action: 'captured',
        actor: { id: 'source.channel-quote', label: '渠道报价监测', type: 'system' },
        kind: 'event.state_changed',
        occurredAt: '2026-05-28T09:12:00+08:00',
        outcome: 'captured -> analyzing',
        summary: 'NAND 报价试探事件进入分析中，等待下游接单验证。',
      },
      {
        action: 'analysis_scored',
        actor: { id: 'scoring.engine', label: 'Scoring Engine', type: 'system' },
        kind: 'analysis.scored',
        occurredAt: '2026-05-28T09:24:00+08:00',
        outcome: 'awaiting verification',
        summary: '事件影响较强，但因信源仍待验证，建议只进入复核观察。',
      },
    ],
  },
  'evt-semiconductor-foundry': {
    availability: {
      message: '后端事件审计接口未接通，当前展示结构化占位数据。',
      state: 'degraded',
    },
    eventId: 'evt-semiconductor-foundry',
    nodes: [
      {
        action: 'request_reanalysis',
        actor: { id: 'operator.risk', label: '风险复核人', type: 'human' },
        approvalId: 'apr-foundry-03',
        kind: 'reanalysis.requested',
        occurredAt: '2026-05-28T09:06:00+08:00',
        outcome: 'manual review requested',
        summary: '正式口径与渠道消息冲突，人工要求保留减仓建议但等待二次确认。',
        traceId: 'evt-conflict-319',
      },
      {
        action: 'amend',
        actor: { id: 'operator.risk', label: '风险复核人', type: 'human' },
        approvalId: 'apr-foundry-03',
        kind: 'approval.resolved',
        occurredAt: '2026-05-28T09:20:00+08:00',
        outcome: 'amended summary',
        summary: '将审批备注修改为“信源冲突下维持人工确认，不自动放行”。',
        traceId: 'evt-conflict-319',
      },
    ],
  },
}

export function createEmptyEventAuditTimeline(eventId: string): EventAuditTimelineResponse {
  return {
    availability: {
      message: '当前事件暂无审计记录。',
      state: 'empty',
    },
    eventId,
    nodes: [],
  }
}

export function createUnavailableEventAuditTimeline(eventId: string): EventAuditTimelineResponse {
  return {
    availability: {
      message: '后端事件审计接口未接通，当前没有可用占位数据。',
      state: 'unavailable',
    },
    eventId,
    nodes: [],
  }
}

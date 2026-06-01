import type { HealthAlert } from '@/features/mainflow/mock-data'

import type { EventScoreCardModel } from '../types/event-scoring.types'

export function createHealthAlertEventCardModel(
  alert: HealthAlert,
  fallbackEvent: EventScoreCardModel,
): EventScoreCardModel {
  return {
    ...fallbackEvent,
    id: alert.id,
    title: alert.title,
    summary: alert.summary,
    actionHint: alert.traceHint,
    impactDirection: '运行风险提示',
    industries: ['Runtime'],
    source: '系统健康',
    status: 'warning',
    sourceType: '内部监控',
    degradationNotices: [],
    score: {
      ...fallbackEvent.score,
      sourceAuthority: 'C',
      eventReliability: 24,
      impactStrength: 38,
      freshness: 'high',
      eventPriority: 40,
      priorityBand: 'C',
      verificationStatus: 'single_source',
      analysisConfidence: 0,
      recommendationScore: 0,
      uncertaintySummary: '这里只做轻量运行提醒，不进入正式评分驱动排序。',
      selectionReason: '运行态提醒，不参与高价值事件打分',
    },
    analysisHighlights: {
      support: '提醒会帮助操盘者在浏览事件时同步感知运行风险。',
      opposition: '这类系统健康信号不应替代正式事件评分或高价值排序。',
      verificationNote: '当前只做轻量提醒，真实排障入口仍在 Runtime。',
    },
  }
}

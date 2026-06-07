import type { EventAgentStageStatus, EventDecision, EventStatus, EventTimelineStatus } from '../types';

export function formatEventDecision(value: EventDecision): string {
  switch (value) {
    case 'route':
      return '进入分析';
    case 'review':
      return '需要复核';
    case 'discard':
      return '已丢弃';
  }
}

export function formatEventStatus(value: EventStatus | EventAgentStageStatus | EventTimelineStatus): string {
  switch (value) {
    case 'success':
      return '成功';
    case 'failed':
      return '失败';
    case 'warning':
      return '警告';
    case 'unavailable':
      return '不可用';
  }
}

export function eventDecisionTone(value: EventDecision): string {
  switch (value) {
    case 'route':
      return 'bg-emerald-50 text-emerald-700';
    case 'review':
      return 'bg-amber-50 text-amber-700';
    case 'discard':
      return 'bg-slate-100 text-slate-600';
  }
}

export function eventStatusTone(value: EventStatus | EventAgentStageStatus | EventTimelineStatus): string {
  switch (value) {
    case 'success':
      return 'bg-emerald-50 text-emerald-700';
    case 'failed':
      return 'bg-rose-50 text-rose-700';
    case 'warning':
      return 'bg-amber-50 text-amber-700';
    case 'unavailable':
      return 'bg-slate-100 text-slate-600';
  }
}

export function formatEventDate(value: string | null): string {
  if (!value) {
    return '未记录';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

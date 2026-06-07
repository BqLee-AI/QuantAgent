export type EventScoreLevel = 'A' | 'B' | 'C' | 'S';

export interface EventScoreTone {
  label: string;
  panelClass: string;
  scoreClass: string;
  tagClass: string;
}

export const scoreNeutralTone: Pick<EventScoreTone, 'panelClass' | 'scoreClass' | 'tagClass'> = {
  panelClass: 'border border-[var(--qa-score-neutral-border)] bg-[var(--qa-score-neutral-panel)]',
  scoreClass: 'border border-[var(--qa-score-neutral-border)] bg-[var(--qa-score-neutral-bg)] text-[var(--qa-score-neutral-fg)]',
  tagClass: 'border border-[var(--qa-score-neutral-border)] bg-[var(--qa-score-neutral-bg)] text-[var(--qa-score-neutral-fg)]',
};

const scoreToneTokens = {
  priorityStrong: {
    panelClass: 'border border-[var(--qa-score-priority-border)] bg-[var(--qa-score-priority-panel)]',
    scoreClass: 'bg-[var(--qa-score-priority-strong)] text-[var(--qa-score-priority-on-strong)] shadow-[0_10px_24px_rgb(190_24_93/0.18)]',
    tagClass: 'bg-[var(--qa-score-priority-strong)] text-[var(--qa-score-priority-on-strong)] shadow-[0_10px_24px_rgb(190_24_93/0.18)]',
  },
  prioritySoft: {
    panelClass: 'border border-[var(--qa-score-priority-border)] bg-[var(--qa-score-priority-panel)]',
    scoreClass: 'border border-[var(--qa-score-priority-border)] bg-[var(--qa-score-priority-bg)] text-[var(--qa-score-priority-fg)]',
    tagClass: 'border border-[var(--qa-score-priority-border)] bg-[var(--qa-score-priority-bg)] text-[var(--qa-score-priority-fg)]',
  },
  actionSoft: {
    panelClass: 'border border-[var(--qa-score-action-border)] bg-[var(--qa-score-action-panel)]',
    scoreClass: 'border border-[var(--qa-score-action-border)] bg-[var(--qa-score-action-bg)] text-[var(--qa-score-action-fg)]',
    tagClass: 'border border-[var(--qa-score-action-border)] bg-[var(--qa-score-action-bg)] text-[var(--qa-score-action-fg)]',
  },
  reliabilityStrong: {
    panelClass: 'border border-[var(--qa-score-reliability-border)] bg-[var(--qa-score-reliability-panel)]',
    scoreClass: 'bg-[var(--qa-score-reliability-strong)] text-[var(--qa-score-on-strong)] shadow-[0_10px_24px_rgb(13_148_136/0.16)]',
    tagClass: 'bg-[var(--qa-score-reliability-strong)] text-[var(--qa-score-on-strong)] shadow-[0_10px_24px_rgb(13_148_136/0.16)]',
  },
  reliabilitySoft: {
    panelClass: 'border border-[var(--qa-score-reliability-border)] bg-[var(--qa-score-reliability-panel)]',
    scoreClass: 'border border-[var(--qa-score-reliability-border)] bg-[var(--qa-score-reliability-bg)] text-[var(--qa-score-reliability-fg)]',
    tagClass: 'border border-[var(--qa-score-reliability-border)] bg-[var(--qa-score-reliability-bg)] text-[var(--qa-score-reliability-fg)]',
  },
  attentionSoft: {
    panelClass: 'border border-[var(--qa-score-attention-border)] bg-[var(--qa-score-attention-panel)]',
    scoreClass: 'border border-[var(--qa-score-attention-border)] bg-[var(--qa-score-attention-bg)] text-[var(--qa-score-attention-fg)]',
    tagClass: 'border border-[var(--qa-score-attention-border)] bg-[var(--qa-score-attention-bg)] text-[var(--qa-score-attention-fg)]',
  },
};

export function getPriorityTone(priorityBand: EventScoreLevel, score: number): EventScoreTone {
  if (priorityBand === 'S') {
    return { label: '重点', ...scoreToneTokens.priorityStrong };
  }

  if (priorityBand === 'A') {
    return { label: '关注', ...scoreToneTokens.prioritySoft };
  }

  if (priorityBand === 'B') {
    return { label: '观察', ...scoreToneTokens.attentionSoft };
  }

  if (score >= 70) {
    return { label: '关注', ...scoreToneTokens.prioritySoft };
  }

  return { label: '记录', ...scoreNeutralTone };
}

export function getReliabilityTone(score: number): EventScoreTone {
  if (score < 60) {
    return { label: '低分记录', ...scoreNeutralTone };
  }

  if (score >= 90) {
    return { label: '极高可信', ...scoreToneTokens.reliabilityStrong };
  }

  if (score >= 80) {
    return { label: '高可信', ...scoreToneTokens.reliabilitySoft };
  }

  if (score >= 70) {
    return { label: '中等可信', ...scoreToneTokens.attentionSoft };
  }

  return { label: '待增强', ...scoreToneTokens.actionSoft };
}

export function getImpactTone(score: number): EventScoreTone {
  if (score < 60) {
    return { label: '低分记录', ...scoreNeutralTone };
  }

  if (score >= 90) {
    return { label: '极强影响', ...scoreToneTokens.prioritySoft };
  }

  if (score >= 80) {
    return { label: '高影响', ...scoreToneTokens.actionSoft };
  }

  if (score >= 70) {
    return { label: '中高影响', ...scoreToneTokens.attentionSoft };
  }

  return { label: '中等影响', ...scoreNeutralTone };
}

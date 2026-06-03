import { describe, expect, it } from 'vitest';

import {
  formatRuntimeAuditStage,
  formatRuntimeAuditTimeline,
  getRuntimeAuditStatusTone,
} from './runtime-audit-format';

describe('runtime audit format helpers', () => {
  it('formats timeline stage labels without topic names', () => {
    expect(formatRuntimeAuditStage('ai_intake_unavailable')).toBe('AI intake 暂不可审计');
    expect(formatRuntimeAuditStage('route_decided')).toBe('路由结果已审计');
    expect(formatRuntimeAuditTimeline([
      { step_id: 'captured' },
      { step_id: 'persisted' },
      { step_id: 'scheduler_linked' },
      { step_id: 'ai_intake_routed' },
      { step_id: 'route_decided' },
      { step_id: 'route_unavailable' },
    ])).toBe('采集 -> RawEvent 入库 -> 调度关联 -> AI intake 已审计 -> 路由结果已审计 -> 路由结果暂不可审计');
  });

  it('formats unavailable status with neutral tone', () => {
    expect(getRuntimeAuditStatusTone('unavailable')).toContain('text-muted-strong');
  });
});

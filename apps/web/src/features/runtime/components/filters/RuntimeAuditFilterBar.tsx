import {
  Button,
  Input,
  TextField,
} from '@heroui/react';

import type {
  RuntimeAuditDecision,
  RuntimeAuditFilters,
  RuntimeAuditStatus,
} from '../../types';

interface RuntimeAuditFilterBarProps {
  filters: RuntimeAuditFilters;
  onReset: () => void;
  onUpdate: <TKey extends keyof RuntimeAuditFilters>(
    key: TKey,
    value: RuntimeAuditFilters[TKey],
  ) => void;
}

export function RuntimeAuditFilterBar({
  filters,
  onReset,
  onUpdate,
}: RuntimeAuditFilterBarProps) {
  return (
    <section className="rounded-xl border border-hairline bg-canvas px-4 py-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[repeat(7,minmax(0,1fr))_auto]">
        <TextField
          aria-label="event_id"
          value={filters.event_id}
          onChange={(value) => onUpdate('event_id', value)}
        >
          <Input className="w-full" placeholder="event_id" variant="secondary" />
        </TextField>
        <TextField
          aria-label="trace_id"
          value={filters.trace_id}
          onChange={(value) => onUpdate('trace_id', value)}
        >
          <Input className="w-full" placeholder="trace_id" variant="secondary" />
        </TextField>
        <TextField
          aria-label="industry"
          value={filters.industry}
          onChange={(value) => onUpdate('industry', value)}
        >
          <Input className="w-full" placeholder="industry" variant="secondary" />
        </TextField>
        <select
          className="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-body-sm text-ink"
          value={filters.decision}
          onChange={(event) => onUpdate('decision', event.target.value as RuntimeAuditDecision | 'all')}
        >
          {decisionOptions.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <select
          className="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-body-sm text-ink"
          value={filters.status}
          onChange={(event) => onUpdate('status', event.target.value as RuntimeAuditStatus | 'all')}
        >
          {statusOptions.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <TextField
          aria-label="time_from"
          value={filters.time_from}
          onChange={(value) => onUpdate('time_from', value)}
        >
          <Input className="w-full" placeholder="time_from" variant="secondary" />
        </TextField>
        <TextField
          aria-label="time_to"
          value={filters.time_to}
          onChange={(value) => onUpdate('time_to', value)}
        >
          <Input className="w-full" placeholder="time_to" variant="secondary" />
        </TextField>
        <Button className="h-10" type="button" variant="outline" onPress={onReset}>
          清空
        </Button>
      </div>
    </section>
  );
}

const decisionOptions: Array<{ label: string; value: RuntimeAuditDecision | 'all' }> = [
  { label: '全部决策', value: 'all' },
  { label: 'Route', value: 'route' },
  { label: 'Discard', value: 'discard' },
  { label: 'Review', value: 'review' },
];

const statusOptions: Array<{ label: string; value: RuntimeAuditStatus | 'all' }> = [
  { label: '全部状态', value: 'all' },
  { label: '成功', value: 'success' },
  { label: '警告', value: 'warning' },
  { label: '错误', value: 'error' },
  { label: '等待', value: 'pending' },
  { label: '不可用', value: 'unavailable' },
];

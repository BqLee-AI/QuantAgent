import {
  Button,
  Input,
  TextField,
} from '@heroui/react';

import type {
  RuntimeAuditFilters,
  RuntimeAuditNewsStage,
  RuntimeAuditNewsStatus,
} from '../../types';
import { formatRuntimeAuditStage, formatRuntimeAuditStatus } from '../../utils';

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
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[repeat(9,minmax(0,1fr))_auto]">
        <TextField
          aria-label="keyword"
          value={filters.keyword}
          onChange={(value) => onUpdate('keyword', value)}
        >
          <Input className="w-full" placeholder="标题 / URL / 摘要" variant="secondary" />
        </TextField>
        <TextField
          aria-label="binding_id"
          value={filters.binding_id}
          onChange={(value) => onUpdate('binding_id', value)}
        >
          <Input className="w-full" placeholder="binding_id" variant="secondary" />
        </TextField>
        <TextField
          aria-label="source_plugin_id"
          value={filters.source_plugin_id}
          onChange={(value) => onUpdate('source_plugin_id', value)}
        >
          <Input className="w-full" placeholder="source_plugin_id" variant="secondary" />
        </TextField>
        <select
          className="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-body-sm text-ink"
          value={filters.status}
          onChange={(event) => onUpdate('status', event.target.value as RuntimeAuditNewsStatus | 'all')}
        >
          {statusOptions.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <select
          className="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-body-sm text-ink"
          value={filters.current_stage}
          onChange={(event) => onUpdate('current_stage', event.target.value as RuntimeAuditNewsStage | 'all')}
        >
          {stageOptions.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <TextField
          aria-label="trace_id"
          value={filters.trace_id}
          onChange={(value) => onUpdate('trace_id', value)}
        >
          <Input className="w-full" placeholder="trace_id" variant="secondary" />
        </TextField>
        <TextField
          aria-label="request_id"
          value={filters.request_id}
          onChange={(value) => onUpdate('request_id', value)}
        >
          <Input className="w-full" placeholder="request_id" variant="secondary" />
        </TextField>
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

const statusOptions: Array<{ label: string; value: RuntimeAuditNewsStatus | 'all' }> = [
  { label: '全部状态', value: 'all' },
  { label: formatRuntimeAuditStatus('captured'), value: 'captured' },
  { label: formatRuntimeAuditStatus('linked'), value: 'linked' },
  { label: formatRuntimeAuditStatus('pending'), value: 'pending' },
  { label: formatRuntimeAuditStatus('routed'), value: 'routed' },
  { label: formatRuntimeAuditStatus('unavailable'), value: 'unavailable' },
];

const stageOptions: Array<{ label: string; value: RuntimeAuditNewsStage | 'all' }> = [
  { label: '全部阶段', value: 'all' },
  { label: formatRuntimeAuditStage('captured'), value: 'captured' },
  { label: formatRuntimeAuditStage('persisted'), value: 'persisted' },
  { label: formatRuntimeAuditStage('scheduler_linked'), value: 'scheduler_linked' },
  { label: formatRuntimeAuditStage('ai_intake_unavailable'), value: 'ai_intake_unavailable' },
  { label: formatRuntimeAuditStage('ai_intake_routed'), value: 'ai_intake_routed' },
  { label: formatRuntimeAuditStage('route_decided'), value: 'route_decided' },
  { label: formatRuntimeAuditStage('route_unavailable'), value: 'route_unavailable' },
];

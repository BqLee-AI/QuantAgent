import { Chip } from '@heroui/react';

import type { ModelConfig, ModelInvocation } from '../api';
import { ModelInvocationTable } from './ModelInvocationTable';

interface ModelStatusPanelProps {
  config: ModelConfig | undefined;
  invocations: readonly ModelInvocation[];
  invocationsError: boolean;
  invocationsLoading: boolean;
}

export function ModelStatusPanel({
  config,
  invocations,
  invocationsError,
  invocationsLoading,
}: ModelStatusPanelProps) {
  const latestInvocation = invocations[0] ?? null;
  const tokenTotal = invocations.reduce((sum, item) => sum + (item.token_usage.total_tokens ?? 0), 0);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-slate-950">状态与统计</h2>
        <p className="mt-1 text-sm text-slate-500">这里只展示脱敏状态、最近调用和 token usage。</p>
      </div>

      <div className="mb-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Stat label="配置状态" value={<StatusChip value={config?.status ?? 'loading'} />} />
        <Stat label="Key 状态" value={<StatusChip value={config?.key_status ?? 'loading'} />} />
        <Stat label="Masked key" value={config?.masked_key ?? '-'} />
        <Stat label="累计 total tokens" value={String(tokenTotal)} />
        <Stat label="最近模型" value={latestInvocation?.model ?? config?.model ?? '-'} />
        <Stat label="最近错误" value={config?.last_error ?? latestInvocation?.error_summary ?? '-'} />
      </div>

      <ModelInvocationTable
        invocations={invocations}
        isError={invocationsError}
        isLoading={invocationsLoading}
      />
    </section>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
      <span className="block text-xs font-medium uppercase tracking-normal text-slate-500">{label}</span>
      <span className="mt-1 block break-words text-sm font-semibold text-slate-950">{value}</span>
    </div>
  );
}

function StatusChip({ value }: { value: string }) {
  const color = value === 'configured' || value === 'succeeded' ? 'success' : value === 'failed' ? 'danger' : 'warning';

  return (
    <Chip color={color} size="sm" variant="soft">
      {value}
    </Chip>
  );
}

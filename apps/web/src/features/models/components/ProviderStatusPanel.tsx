import { Chip } from '@heroui/react';

import type { ModelInvocation, ModelProviderDetail } from '../api';
import { ModelInvocationTable } from './ModelInvocationTable';

interface ProviderStatusPanelProps {
  invocations: readonly ModelInvocation[];
  invocationsError: boolean;
  invocationsLoading: boolean;
  provider: ModelProviderDetail | undefined;
}

export function ProviderStatusPanel({
  invocations,
  invocationsError,
  invocationsLoading,
  provider,
}: ProviderStatusPanelProps) {
  const latestInvocation = invocations[0] ?? null;
  const tokenTotal = invocations.reduce((sum, item) => sum + (item.token_usage.total_tokens ?? 0), 0);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-slate-950">状态与统计</h2>
        <p className="mt-1 text-sm text-slate-500">展示当前 provider 的配置状态、最近错误和最近调用。</p>
      </div>

      <div className="mb-5 grid gap-3 md:grid-cols-2">
        <Stat label="配置状态" value={<StatusChip value={provider?.status ?? 'loading'} />} />
        <Stat label="Key 状态" value={<StatusChip value={provider?.key_status ?? 'loading'} />} />
        <Stat label="默认 Provider" value={provider?.is_default ? '是' : '否'} />
        <Stat label="模型数量" value={String(provider?.model_count ?? 0)} />
        <Stat label="Masked key" value={provider?.masked_key ?? '-'} />
        <Stat label="累计 total tokens" value={String(tokenTotal)} />
        <Stat label="最近错误" value={provider?.last_error ?? latestInvocation?.error_summary ?? '-'} />
        <Stat label="最近预设" value={latestInvocation?.preset_key ?? '-'} />
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

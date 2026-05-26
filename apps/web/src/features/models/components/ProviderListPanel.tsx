import { Button, Chip } from '@heroui/react';

import type { ModelProviderSummary } from '../api';

interface ProviderListPanelProps {
  currentFilter: 'all' | 'default' | 'enabled' | 'failed' | 'missing_key';
  isLoading: boolean;
  onCreate: () => void;
  onFilterChange: (filter: 'all' | 'default' | 'enabled' | 'failed' | 'missing_key') => void;
  onSearchChange: (value: string) => void;
  onSelect: (providerId: number) => void;
  onSetDefault: (providerId: number) => void;
  providers: readonly ModelProviderSummary[];
  searchValue: string;
  selectedProviderId: number | null;
  settingDefaultProviderId: number | null;
}

export function ProviderListPanel({
  currentFilter,
  isLoading,
  onCreate,
  onFilterChange,
  onSearchChange,
  onSelect,
  onSetDefault,
  providers,
  searchValue,
  selectedProviderId,
  settingDefaultProviderId,
}: ProviderListPanelProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">供应商列表</h2>
          <p className="mt-1 text-sm text-slate-500">浏览 provider 状态、默认项和模型数量。</p>
        </div>
        <Button type="button" variant="primary" onPress={onCreate}>
          新增 Provider
        </Button>
      </div>

      <div className="mb-4 grid gap-3">
        <input
          className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-blue-500"
          placeholder="搜索 provider 名称..."
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {[
            ['all', '全部'],
            ['enabled', '已启用'],
            ['default', '默认'],
            ['failed', '异常'],
            ['missing_key', '缺少 Key'],
          ].map(([value, label]) => (
            <button
              key={value}
              className={
                currentFilter === value
                  ? 'rounded-full border border-blue-500 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700'
                  : 'rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 hover:border-slate-300'
              }
              type="button"
              onClick={() => onFilterChange(value as ProviderListPanelProps['currentFilter'])}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {providers.length === 0 ? (
        <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">
          {isLoading ? '加载 provider 列表...' : '还没有模型 provider，先创建第一条配置。'}
        </p>
      ) : (
        <div className="grid gap-3">
          {providers.map((provider) => {
            const selected = selectedProviderId === provider.id;

            return (
              <button
                key={provider.id}
                className={
                  selected
                    ? 'rounded-md border border-blue-500 bg-blue-50 px-3 py-3 text-left shadow-sm'
                    : 'rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-left hover:border-slate-300 hover:bg-white'
                }
                type="button"
                onClick={() => onSelect(provider.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-semibold text-slate-950">{provider.name}</span>
                      {provider.is_default ? <Chip color="accent" size="sm" variant="soft">默认</Chip> : null}
                      <Chip color={chipColor(provider.status)} size="sm" variant="soft">
                        {statusLabel(provider.status)}
                      </Chip>
                      <Chip color={provider.enabled ? 'success' : 'default'} size="sm" variant="soft">
                        {provider.enabled ? '已启用' : '已禁用'}
                      </Chip>
                    </div>
                    <p className="mt-2 truncate text-xs text-slate-500">
                      {provider.base_url ?? '使用默认 OpenAI 兼容端点'}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600">
                      <span>模型数 {provider.model_count}</span>
                      <span>{provider.key_status === 'configured' ? 'Key 已配置' : '缺少 Key'}</span>
                    </div>
                  </div>

                  <Button
                    isDisabled={provider.is_default || settingDefaultProviderId === provider.id}
                    size="sm"
                    type="button"
                    variant="outline"
                    onPress={() => onSetDefault(provider.id)}
                  >
                    {settingDefaultProviderId === provider.id ? '设置中...' : '设为默认'}
                  </Button>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

function chipColor(status: ModelProviderSummary['status']) {
  if (status === 'configured') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  return 'warning';
}

function statusLabel(status: ModelProviderSummary['status']) {
  if (status === 'configured') {
    return '可用';
  }
  if (status === 'failed') {
    return '异常';
  }
  if (status === 'missing_key') {
    return '缺少 Key';
  }
  return '已禁用';
}

import { useMemo } from 'react';

import type { ModelProviderSummary } from '../../api';
import { type ProviderPresetDefinition, providerPresets } from '../../provider-presets';
import type { ProviderListItem } from '../../types';
import { ProviderAvatar } from '../shared/ProviderAvatar';

type ProviderStateFilter = 'all' | 'enabled' | 'default' | 'failed' | 'missing_key';

function findPresetForProvider(provider: ModelProviderSummary): ProviderPresetDefinition | undefined {
  return providerPresets.find((preset) => preset.draft.name.toLowerCase() === provider.name.toLowerCase());
}

interface ProviderListPanelProps {
  providers: readonly ModelProviderSummary[];
  isLoading: boolean;
  providerEnabledOverrides?: Readonly<Record<string, boolean>>;
  /** 当前选中的列表项（preset key 或 provider id） */
  selectedKey: string | null;
  onSearchChange: (value: string) => void;
  onSelectItem: (item: ProviderListItem) => void;
  searchValue: string;
  stateFilter: ProviderStateFilter;
  onStateFilterChange: (value: ProviderStateFilter) => void;
}

export function ProviderListPanel({
  providers,
  isLoading,
  providerEnabledOverrides,
  selectedKey,
  onSearchChange,
  onSelectItem,
  searchValue,
  stateFilter,
  onStateFilterChange,
}: ProviderListPanelProps) {
  /** 合并预设 + 已配置的供应商，去重 */
  const listItems = useMemo(() => {
    const items: ProviderListItem[] = [];
    const matchedProviderIds = new Set<number>();

    // 按预设顺序，把所有预设放进去
    for (const preset of providerPresets) {
      const matched = providers.find(
        (p) => p.name.toLowerCase() === preset.draft.name.toLowerCase(),
      );
      if (matched) {
        matchedProviderIds.add(matched.id);
      }
      items.push({
        providerId: matched?.id ?? null,
        presetId: preset.id,
        name: matched?.name ?? preset.name,
        isConfigured: matched !== undefined,
        summary: matched,
      });
    }

    for (const provider of providers) {
      if (matchedProviderIds.has(provider.id)) continue;
      items.push({
        providerId: provider.id,
        presetId: findPresetForProvider(provider)?.id ?? 'custom',
        name: provider.name,
        isConfigured: true,
        summary: provider,
      });
    }

    let filteredItems = items;

    if (stateFilter !== 'all') {
      filteredItems = filteredItems.filter((item) => {
        const summary = item.summary;
        if (!summary) return false;
        if (stateFilter === 'enabled') return summary.enabled;
        if (stateFilter === 'default') return summary.is_default;
        if (stateFilter === 'failed') return summary.status === 'failed';
        return summary.status === 'missing_key';
      });
    }

    if (searchValue.trim()) {
      const q = searchValue.trim().toLowerCase();
      filteredItems = filteredItems.filter((item) => item.name.toLowerCase().includes(q));
    }
    return filteredItems;
  }, [providers, searchValue, stateFilter]);

  return (
    <section className="flex h-full flex-col overflow-hidden rounded-xl border border-hairline bg-canvas">
      {/* Header */}
      <div className="border-b border-hairline px-4 py-3">
        <h2 className="text-[15px] font-semibold text-ink">供应商</h2>
      </div>

      {/* Search */}
      <div className="border-b border-hairline px-4 py-2.5">
        <input
          className="h-9 w-full rounded-lg border border-hairline bg-surface-soft px-3 text-[13px] text-ink outline-none placeholder:text-muted focus:border-primary"
          placeholder="搜索供应商..."
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {stateFilters.map((filter) => (
            <button
              key={filter.value}
              className={
                stateFilter === filter.value
                  ? 'rounded-full bg-primary px-2.5 py-1 text-[11px] font-semibold text-on-primary'
                  : 'rounded-full bg-surface-card px-2.5 py-1 text-[11px] font-semibold text-muted-strong hover:text-ink'
              }
              type="button"
              onClick={() => onStateFilterChange(filter.value)}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && providers.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
            <span className="text-lg">⏳</span>
            <p className="text-[13px] text-muted">加载中...</p>
          </div>
        ) : listItems.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
            <span className="text-lg">📡</span>
            <p className="text-[13px] text-muted">没有匹配的供应商</p>
          </div>
        ) : (
          <div className="flex flex-col">
            {listItems.map((item) => {
              const itemKey = item.isConfigured ? `p-${item.providerId}` : `preset-${item.presetId}`;
              const isSelected = selectedKey === itemKey;
              const preset = providerPresets.find((p) => p.id === item.presetId);

              return (
                <ProviderRow
                  key={itemKey}
                  enabledOverride={providerEnabledOverrides?.[itemKey]}
                  isSelected={isSelected}
                  item={item}
                  preset={preset}
                  onSelect={() => onSelectItem(item)}
                />
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

const stateFilters: Array<{ label: string; value: ProviderStateFilter }> = [
  { label: '全部', value: 'all' },
  { label: '已启用', value: 'enabled' },
  { label: '默认', value: 'default' },
  { label: '异常', value: 'failed' },
  { label: '缺 Key', value: 'missing_key' },
];

function ProviderRow({
  enabledOverride,
  isSelected,
  item,
  preset,
  onSelect,
}: {
  enabledOverride?: boolean;
  isSelected: boolean;
  item: ProviderListItem;
  preset: ProviderPresetDefinition | undefined;
  onSelect: () => void;
}) {
  const displayName = item.name;
  const effectiveEnabled = typeof enabledOverride === 'boolean' ? enabledOverride : item.summary?.enabled;
  const isOn = Boolean(effectiveEnabled);
  const statusLabel = item.summary
    ? item.summary.status === 'failed'
      ? '异常'
      : item.summary.status === 'missing_key'
        ? '缺 Key'
        : item.summary.status === 'disabled'
          ? '已停用'
          : '可用'
    : '未配置';
  const statusClass = item.summary?.status === 'failed'
    ? 'bg-trading-down/12 text-trading-down'
    : item.summary?.status === 'missing_key'
      ? 'bg-amber-100 text-amber-700'
      : item.summary?.status === 'configured'
        ? 'bg-trading-up/12 text-trading-up'
        : 'bg-surface-card text-muted-strong';

  return (
    <button
      className={
        isSelected
          ? 'flex w-full items-center gap-3 border-l-2 border-l-primary bg-surface-soft px-4 py-3 text-left transition-colors'
          : 'flex w-full items-center gap-3 border-l-2 border-l-transparent px-4 py-3 text-left transition-colors hover:bg-surface-soft'
      }
      type="button"
      onClick={onSelect}
    >
      <ProviderAvatar name={preset?.draft.name ?? displayName} size={28} />

      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-[13px] font-semibold text-ink">{displayName}</span>
          {item.summary?.is_default ? (
            <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-on-primary">
              默认
            </span>
          ) : null}
          {isOn ? (
            <span className="shrink-0 rounded-full bg-trading-up/12 px-2 py-0.5 text-[10px] font-semibold text-trading-up">
              On
            </span>
          ) : null}
        </div>
        <div className="mt-1 flex min-w-0 items-center gap-2 text-[11px] text-muted">
          <span className={`shrink-0 rounded-full px-2 py-0.5 font-semibold ${statusClass}`}>{statusLabel}</span>
          <span className="shrink-0">{item.summary?.model_count ?? 0} models</span>
          {item.summary?.updated_at ? (
            <span className="truncate">{new Date(item.summary.updated_at).toLocaleDateString()}</span>
          ) : null}
        </div>
      </div>
    </button>
  );
}

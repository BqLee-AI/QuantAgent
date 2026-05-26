import { Button } from '@heroui/react';
import { useEffect, useMemo, useState } from 'react';

import { formatModelApiError } from '../errors';
import {
  useCreateModelProviderMutation,
  useCreateProviderModelMutation,
  useDeleteProviderModelMutation,
  useModelInvocationsQuery,
  useModelProviderDetailsQueries,
  useModelPresetsQuery,
  useModelProviderQuery,
  useModelProvidersQuery,
  useSetDefaultModelProviderMutation,
  useTestModelProviderConnectionMutation,
  useUpdateModelPresetMutation,
  useUpdateModelProviderMutation,
  useUpdateProviderModelMutation,
} from '../queries';
import { ModelPresetBoard } from './ModelPresetBoard';
import { ProviderEditorForm } from './ProviderEditorForm';
import { ProviderListPanel } from './ProviderListPanel';
import { ProviderStatusPanel } from './ProviderStatusPanel';

type ModelsView = 'providers' | 'presets';
type ProviderFilter = 'all' | 'default' | 'enabled' | 'failed' | 'missing_key';

export function ModelsPage() {
  const providersQuery = useModelProvidersQuery();
  const presetsQuery = useModelPresetsQuery();
  const [activeView, setActiveView] = useState<ModelsView>('providers');
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>('all');
  const [providerSearch, setProviderSearch] = useState('');
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (isCreating) {
      return;
    }
    if (!providersQuery.data?.providers.length) {
      setSelectedProviderId(null);
      return;
    }
    if (selectedProviderId !== null && providersQuery.data.providers.some((provider) => provider.id === selectedProviderId)) {
      return;
    }
    setSelectedProviderId(
      providersQuery.data.default_provider_id ?? providersQuery.data.providers[0]?.id ?? null,
    );
  }, [isCreating, providersQuery.data, selectedProviderId]);

  const providerQuery = useModelProviderQuery(isCreating ? null : selectedProviderId);
  const providerDetailsQueries = useModelProviderDetailsQueries(
    providersQuery.data?.providers.map((provider) => provider.id) ?? [],
  );
  const providerDetails = useMemo(
    () => providerDetailsQueries.map((query) => query.data).filter((item): item is NonNullable<typeof item> => Boolean(item)),
    [providerDetailsQueries],
  );
  const invocationsQuery = useModelInvocationsQuery(isCreating ? null : selectedProviderId, 'global_default');
  const createMutation = useCreateModelProviderMutation();
  const updateMutation = useUpdateModelProviderMutation(isCreating ? null : selectedProviderId);
  const createProviderModelMutation = useCreateProviderModelMutation(isCreating ? null : selectedProviderId);
  const updateProviderModelMutation = useUpdateProviderModelMutation(isCreating ? null : selectedProviderId);
  const deleteProviderModelMutation = useDeleteProviderModelMutation(isCreating ? null : selectedProviderId);
  const updatePresetMutation = useUpdateModelPresetMutation();
  const setDefaultMutation = useSetDefaultModelProviderMutation();
  const testMutation = useTestModelProviderConnectionMutation(isCreating ? null : selectedProviderId);
  const filteredProviders = useMemo(() => {
    const items = providersQuery.data?.providers ?? [];
    return items.filter((provider) => {
      const searchMatch =
        providerSearch.trim().length === 0 ||
        provider.name.toLowerCase().includes(providerSearch.trim().toLowerCase());
      if (!searchMatch) {
        return false;
      }
      if (providerFilter === 'all') {
        return true;
      }
      if (providerFilter === 'default') {
        return provider.is_default;
      }
      if (providerFilter === 'enabled') {
        return provider.enabled;
      }
      if (providerFilter === 'failed') {
        return provider.status === 'failed';
      }
      return provider.key_status === 'missing';
    });
  }, [providerFilter, providerSearch, providersQuery.data?.providers]);

  return (
    <>
      <section className="page-header">
        <p className="page-kicker">模型</p>
        <h1 className="page-title">模型配置</h1>
        <p className="page-description">
          管理多个供应商、供应商下模型，以及系统固定任务类别的默认模型与基础 fallback。
        </p>
      </section>

      <div className="mb-5 flex gap-3">
        <Button
          type="button"
          variant={activeView === 'providers' ? 'primary' : 'outline'}
          onPress={() => setActiveView('providers')}
        >
          供应商配置
        </Button>
        <Button
          type="button"
          variant={activeView === 'presets' ? 'primary' : 'outline'}
          onPress={() => setActiveView('presets')}
        >
          任务模型预设
        </Button>
      </div>

      {providersQuery.isError ? (
        <p className="mb-4 rounded-md border border-red-900 bg-red-950/60 px-3 py-2 text-sm text-red-300">
          Provider 列表加载失败：{formatModelApiError(providersQuery.error) ?? '未知错误'}
        </p>
      ) : null}

      {activeView === 'providers' ? (
        <section className="grid gap-4 xl:grid-cols-[340px_minmax(460px,0.95fr)_minmax(0,1.05fr)]">
          <ProviderListPanel
            currentFilter={providerFilter}
            isLoading={providersQuery.isLoading}
            onCreate={() => {
              setIsCreating(true);
              setSelectedProviderId(null);
            }}
            onFilterChange={setProviderFilter}
            onSearchChange={setProviderSearch}
            onSelect={(providerId) => {
              setIsCreating(false);
              setSelectedProviderId(providerId);
            }}
            onSetDefault={(providerId) => setDefaultMutation.mutate(providerId)}
            providers={filteredProviders}
            searchValue={providerSearch}
            selectedProviderId={selectedProviderId}
            settingDefaultProviderId={setDefaultMutation.variables ?? null}
          />

          <ProviderEditorForm
            isCreating={isCreating}
            isLoading={providerQuery.isLoading}
            isSaving={createMutation.isPending || updateMutation.isPending}
            isTesting={testMutation.isPending}
            provider={providerQuery.data}
            saveError={formatModelApiError(createMutation.error) ?? formatModelApiError(updateMutation.error)}
            saveSuccess={createMutation.isSuccess || updateMutation.isSuccess}
            testError={formatModelApiError(testMutation.error)}
            testSuccess={testMutation.isSuccess}
            onCreateModel={(input) => createProviderModelMutation.mutate(input)}
            onDeleteModel={(modelId) => deleteProviderModelMutation.mutate(modelId)}
            onSave={(input) => {
              if (isCreating) {
                createMutation.mutate(input as never, {
                  onSuccess: (provider) => {
                    setIsCreating(false);
                    setSelectedProviderId(provider.id);
                  },
                });
                return;
              }
              updateMutation.mutate(input as never);
            }}
            onTest={() => testMutation.mutate()}
            onUpdateModel={(modelId, input) => updateProviderModelMutation.mutate({ input, modelId })}
          />

          <ProviderStatusPanel
            invocations={invocationsQuery.data ?? []}
            invocationsError={invocationsQuery.isError}
            invocationsLoading={invocationsQuery.isLoading}
            provider={providerQuery.data}
          />
        </section>
      ) : (
        <ModelPresetBoard
          presets={presetsQuery.data ?? []}
          providers={providerDetails}
          updateError={formatModelApiError(updatePresetMutation.error)}
          updatingPresetKey={updatePresetMutation.variables?.presetKey ?? null}
          onSavePreset={(presetKey, primaryModelId, fallbackModelId) =>
            updatePresetMutation.mutate({
              presetKey,
              input: { primary_model_id: primaryModelId, fallback_model_id: fallbackModelId },
            })
          }
        />
      )}
    </>
  );
}

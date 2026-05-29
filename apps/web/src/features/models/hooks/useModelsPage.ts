import { useEffect, useMemo, useState } from 'react';

import type { CreateModelProviderInput, ModelProviderDetail, SaveProviderModelInput } from '../api';
import {
  useCreateModelProviderMutation,
  useCreateProviderModelForProviderMutation,
  useCreateProviderModelMutation,
  useDeleteModelProviderMutation,
  useDeleteProviderModelMutation,
  useFetchRemoteProviderModelsMutation,
  useSetDefaultModelProviderMutation,
  useTestModelProviderConnectionMutation,
  useUpdateModelPresetMutation,
  useUpdateModelProviderMutation,
  useUpdateProviderModelMutation,
} from '../mutations';
import { providerPresets } from '../provider-presets';
import {
  useModelInvocationsQuery,
  useModelPresetsQuery,
  useModelProviderDetailsQueries,
  useModelProviderQuery,
  useModelProvidersQuery,
} from '../queries';
import type { ProviderListItem } from '../types';
import type { CreateProviderDraft } from '../components/provider-list/CreateProviderModal';

export type ModelsView = 'providers' | 'presets';
export type ProviderStateFilter = 'all' | 'enabled' | 'default' | 'failed' | 'missing_key';

function findPresetForProvider(provider: { name: string }) {
  return providerPresets.find((preset) => preset.draft.name.toLowerCase() === provider.name.toLowerCase());
}

export function useModelsPage() {
  const providersQuery = useModelProvidersQuery();
  const presetsQuery = useModelPresetsQuery();

  const [activeView, setActiveView] = useState<ModelsView>('providers');
  const [providerSearch, setProviderSearch] = useState('');
  const [providerStateFilter, setProviderStateFilter] = useState<ProviderStateFilter>('all');
  const [providerEnabledOverrides, setProviderEnabledOverrides] = useState<Record<string, boolean>>({});
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ProviderListItem | null>(null);
  const [createDraft, setCreateDraft] = useState<CreateProviderDraft | null>(null);

  const isCreating = selectedItem !== null && !selectedItem.isConfigured;
  const activeProviderId = selectedItem?.isConfigured ? selectedItem.providerId : null;
  const activePreset = providerPresets.find((preset) => preset.id === selectedItem?.presetId);

  useEffect(() => {
    if (selectedKey) return;
    const firstProvider = providersQuery.data?.providers[0];
    if (firstProvider) {
      const matchedPreset = findPresetForProvider(firstProvider);
      setSelectedKey(`p-${firstProvider.id}`);
      setSelectedItem({
        kind: 'provider',
        providerId: firstProvider.id,
        presetId: matchedPreset?.id ?? 'custom',
        name: firstProvider.name,
        isConfigured: true,
        summary: firstProvider,
      });
      return;
    }
    const firstPreset = providerPresets[0];
    if (!firstPreset) return;
    setSelectedKey(`preset-${firstPreset.id}`);
    setSelectedItem({
      kind: 'preset',
      providerId: null,
      presetId: firstPreset.id,
      name: firstPreset.name,
      isConfigured: false,
    });
  }, [providersQuery.data?.providers, selectedKey]);

  const providerQuery = useModelProviderQuery(activeProviderId);
  const invocationsQuery = useModelInvocationsQuery(activeProviderId, null);
  const providerDetailsQueries = useModelProviderDetailsQueries(
    providersQuery.data?.providers.map((provider) => provider.id) ?? [],
  );
  const providerDetails = useMemo(
    () => providerDetailsQueries.map((query) => query.data).filter((item): item is NonNullable<typeof item> => Boolean(item)),
    [providerDetailsQueries],
  );

  const createMutation = useCreateModelProviderMutation();
  const createModelForProviderMutation = useCreateProviderModelForProviderMutation();
  const updateMutation = useUpdateModelProviderMutation(activeProviderId);
  const deleteProviderMutation = useDeleteModelProviderMutation(activeProviderId);
  const setDefaultProviderMutation = useSetDefaultModelProviderMutation();
  const createProviderModelMutation = useCreateProviderModelMutation(activeProviderId);
  const updateProviderModelMutation = useUpdateProviderModelMutation(activeProviderId);
  const deleteProviderModelMutation = useDeleteProviderModelMutation(activeProviderId);
  const updatePresetMutation = useUpdateModelPresetMutation();
  const testMutation = useTestModelProviderConnectionMutation();
  const remoteModelsMutation = useFetchRemoteProviderModelsMutation();

  function handleSelectItem(item: ProviderListItem) {
    const itemKey = item.kind === 'create'
      ? 'create-provider'
      : item.isConfigured
        ? `p-${item.providerId}`
        : `preset-${item.presetId}`;
    setSelectedKey(itemKey);
    setSelectedItem(item);
    if (item.kind !== 'create') {
      setCreateDraft(null);
    }
  }

  function handleCreateProvider(draft: CreateProviderDraft) {
    setCreateDraft(draft);
    setSelectedKey('create-provider');
    setSelectedItem({
      kind: 'create',
      providerId: null,
      presetId: draft.presetId,
      name: draft.name,
      isConfigured: false,
    });
  }

  function handleCreateWithModel(input: CreateModelProviderInput, model: SaveProviderModelInput | null) {
    return createMutation.mutateAsync(input).then(async (provider) => {
      const providerKey = `p-${provider.id}`;
      const matchedPreset = findPresetForProvider(provider);
      setProviderEnabledOverrides((current) => {
        const next = { ...current };
        const previousEnabled = selectedKey ? current[selectedKey] : undefined;
        next[providerKey] = typeof previousEnabled === 'boolean' ? previousEnabled : provider.enabled;
        if (selectedKey?.startsWith('preset-')) {
          delete next[selectedKey];
        }
        return next;
      });
      setSelectedKey(providerKey);
      setSelectedItem({
        kind: 'provider',
        providerId: provider.id,
        presetId: selectedItem?.presetId ?? matchedPreset?.id ?? 'custom',
        name: provider.name,
        isConfigured: true,
        summary: {
          ...provider,
          model_count: model ? provider.models.length + 1 : provider.models.length,
        },
      });
      if (model) {
        await createModelForProviderMutation.mutateAsync({ input: model, providerId: provider.id });
      }
      return provider;
    });
  }

  async function ensureProviderForTesting(providerOverride?: ModelProviderDetail) {
    if (providerOverride) {
      return providerOverride;
    }
    if (activeProviderId !== null && providerQuery.data) {
      return providerQuery.data;
    }
    if (!isCreating || !activePreset) {
      return null;
    }
    // 中文注释：测试连接前必须保证 provider 已持久化，否则后端无法记录本次检测的审计调用。
    return handleCreateWithModel(
      {
        provider_type: 'openai_compatible',
        name: activePreset.draft.name,
        base_url: activePreset.draft.base_url ?? null,
        api_key: null,
        enabled: true,
        is_default: false,
      },
      {
        enabled: true,
        is_global_default: true,
        model_name: activePreset.draft.example_model,
        supports_vision: activePreset.id === 'openrouter',
      },
    );
  }

  async function handleTestConnection(providerOverride?: ModelProviderDetail) {
    const provider = await ensureProviderForTesting(providerOverride);
    if (!provider) return;
    // 中文注释：检测连接依赖至少一个可用模型；这里在测试前补齐默认模型或重新启用首个模型。
    if (provider.models.length === 0) {
      await createModelForProviderMutation.mutateAsync({
        input: {
          enabled: true,
          is_global_default: true,
          model_name: activePreset?.draft.example_model ?? 'default-model',
          supports_vision: activePreset?.id === 'openrouter',
        },
        providerId: provider.id,
      });
    } else if (!provider.models.some((model) => model.enabled)) {
      const firstModel = provider.models[0];
      if (firstModel && activeProviderId === provider.id) {
        await updateProviderModelMutation.mutateAsync({
          modelId: firstModel.id,
          input: {
            model_name: firstModel.model_name,
            enabled: true,
            supports_vision: firstModel.supports_vision,
            is_global_default: firstModel.is_global_default,
          },
        });
      }
    }
    await testMutation.mutateAsync(provider.id);
  }

  function handleEnabledChange(enabled: boolean) {
    if (!selectedKey) return;
    setProviderEnabledOverrides((current) => ({ ...current, [selectedKey]: enabled }));
  }

  function handleDeleteProvider() {
    if (activeProviderId === null) return;
    deleteProviderMutation.mutate(undefined, {
      onSuccess: () => {
        const deletedPresetId = selectedItem?.presetId ?? null;
        if (deletedPresetId && deletedPresetId !== 'custom') {
          const preset = providerPresets.find((item) => item.id === deletedPresetId);
          setSelectedKey(`preset-${deletedPresetId}`);
          setSelectedItem({
            kind: 'preset',
            providerId: null,
            presetId: deletedPresetId,
            name: preset?.name ?? selectedItem?.name ?? '自定义',
            isConfigured: false,
          });
        } else {
          setSelectedKey(null);
          setSelectedItem(null);
        }
        setProviderEnabledOverrides((current) => {
          if (!selectedKey) return current;
          const next = { ...current };
          delete next[selectedKey];
          return next;
        });
      },
    });
  }

  return {
    activePreset,
    activeProviderId,
    activeView,
    createDraft,
    createModelForProviderMutation,
    createMutation,
    createProviderModelMutation,
    deleteProviderModelMutation,
    deleteProviderMutation,
    ensureProviderForTesting,
    handleCreateWithModel,
    handleCreateProvider,
    handleDeleteProvider,
    handleEnabledChange,
    handleSelectItem,
    handleTestConnection,
    invocationsQuery,
    isCreating,
    presetsQuery,
    providerDetails,
    providerEnabledOverrides,
    providerQuery,
    providerSearch,
    providerStateFilter,
    providersQuery,
    remoteModelsMutation,
    selectedKey,
    setActiveView,
    setDefaultProviderMutation,
    setProviderSearch,
    setProviderStateFilter,
    testMutation,
    updateMutation,
    updatePresetMutation,
    updateProviderModelMutation,
  };
}

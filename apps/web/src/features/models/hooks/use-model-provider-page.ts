import { useEffect, useMemo, useState } from 'react';

import { formatModelApiError } from '../errors';
import {
  useCreateModelProviderMutation,
  useCreateProviderModelMutation,
  useDeleteProviderModelMutation,
  useSetDefaultModelProviderMutation,
  useTestModelProviderConnectionMutation,
  useUpdateModelPresetMutation,
  useUpdateModelProviderMutation,
  useUpdateProviderModelMutation,
} from '../mutations';
import {
  useModelInvocationsQuery,
  useModelPresetsQuery,
  useModelProviderDetailsQueries,
  useModelProviderQuery,
  useModelProvidersQuery,
} from '../queries';

export type ModelsView = 'providers' | 'presets';
export type ProviderFilter = 'all' | 'default' | 'enabled' | 'failed' | 'missing_key';

export function useModelProviderPage() {
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

    if (
      selectedProviderId !== null &&
      providersQuery.data.providers.some((provider) => provider.id === selectedProviderId)
    ) {
      return;
    }

    setSelectedProviderId(
      providersQuery.data.default_provider_id ?? providersQuery.data.providers[0]?.id ?? null,
    );
  }, [isCreating, providersQuery.data, selectedProviderId]);

  const activeProviderId = isCreating ? null : selectedProviderId;
  const providerQuery = useModelProviderQuery(activeProviderId);
  const providerDetailsQueries = useModelProviderDetailsQueries(
    providersQuery.data?.providers.map((provider) => provider.id) ?? [],
  );
  const invocationsQuery = useModelInvocationsQuery(activeProviderId, 'global_default');
  const createMutation = useCreateModelProviderMutation();
  const updateMutation = useUpdateModelProviderMutation(activeProviderId);
  const createProviderModelMutation = useCreateProviderModelMutation(activeProviderId);
  const updateProviderModelMutation = useUpdateProviderModelMutation(activeProviderId);
  const deleteProviderModelMutation = useDeleteProviderModelMutation(activeProviderId);
  const updatePresetMutation = useUpdateModelPresetMutation();
  const setDefaultMutation = useSetDefaultModelProviderMutation();
  const testMutation = useTestModelProviderConnectionMutation(activeProviderId);

  const providerDetails = useMemo(
    () =>
      providerDetailsQueries
        .map((query) => query.data)
        .filter((item): item is NonNullable<typeof item> => Boolean(item)),
    [providerDetailsQueries],
  );

  const filteredProviders = useMemo(() => {
    const items = providersQuery.data?.providers ?? [];
    const search = providerSearch.trim().toLowerCase();

    return items.filter((provider) => {
      const searchMatch = search.length === 0 || provider.name.toLowerCase().includes(search);

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

  const hasSelectedProvider = activeProviderId !== null && providerQuery.data !== undefined;

  // 中文注释：页面级 hook 只组织 query/mutation 与局部状态，组件不再持有底层 API 或 query key。
  return {
    activeView,
    filteredProviders,
    hasSelectedProvider,
    invocationsQuery,
    isCreating,
    providerDetails,
    providerErrorText: providersQuery.isError
      ? formatModelApiError(providersQuery.error) ?? '未知错误'
      : null,
    providerFilter,
    providerQuery,
    providerSearch,
    providersQuery,
    selectedProviderId,
    setActiveView,
    setProviderFilter,
    setProviderSearch,
    setSelectedProviderId,
    startCreating: () => {
      setIsCreating(true);
      setSelectedProviderId(null);
    },
    stopCreating: () => setIsCreating(false),
    mutations: {
      createModel: createProviderModelMutation,
      createProvider: createMutation,
      createProviderErrorText: formatModelApiError(createMutation.error),
      deleteModel: deleteProviderModelMutation,
      setDefaultProvider: setDefaultMutation,
      testConnection: testMutation,
      testConnectionErrorText: formatModelApiError(testMutation.error),
      updateModel: updateProviderModelMutation,
      updatePreset: updatePresetMutation,
      updatePresetErrorText: formatModelApiError(updatePresetMutation.error),
      updateProvider: updateMutation,
      updateProviderErrorText: formatModelApiError(updateMutation.error),
    },
    presetsQuery,
  };
}

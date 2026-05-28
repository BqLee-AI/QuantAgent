import { useQueries, useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type { ModelPresetKey } from '../api';
import { modelQueryKeys } from './model-provider.keys';

export function useModelProvidersQuery() {
  const { modelProviders } = useApis();

  return useQuery({
    queryFn: () => modelProviders.listProviders(),
    queryKey: modelQueryKeys.providers(),
  });
}

export function useModelProviderQuery(providerId: number | null) {
  const { modelProviders } = useApis();

  return useQuery({
    enabled: providerId !== null,
    queryFn: () => {
      if (providerId === null) {
        throw new Error('缺少 provider，无法读取模型供应商详情。');
      }
      return modelProviders.getProvider(providerId);
    },
    queryKey: modelQueryKeys.provider(providerId),
  });
}

export function useModelProviderDetailsQueries(providerIds: readonly number[]) {
  const { modelProviders } = useApis();

  return useQueries({
    queries: providerIds.map((providerId) => ({
      queryFn: () => modelProviders.getProvider(providerId),
      queryKey: modelQueryKeys.provider(providerId),
    })),
  });
}

export function useModelPresetsQuery() {
  const { modelProviders } = useApis();

  return useQuery({
    queryFn: () => modelProviders.listPresets(),
    queryKey: modelQueryKeys.presets(),
  });
}

export function useModelInvocationsQuery(
  providerId: number | null,
  presetKey: ModelPresetKey | null = null,
) {
  const { modelProviders } = useApis();

  return useQuery({
    queryFn: () => modelProviders.listInvocations({ providerId, presetKey }),
    queryKey: modelQueryKeys.invocations(providerId, presetKey),
  });
}

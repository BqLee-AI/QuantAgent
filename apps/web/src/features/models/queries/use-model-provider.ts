import { useQueries, useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import { modelQueryKeys } from './model-provider.keys';

export function useModelProviderQuery(providerId: number | null) {
  const { models } = useApis();

  return useQuery({
    enabled: providerId !== null,
    queryFn: () => models.getProvider(providerId as number),
    queryKey: modelQueryKeys.provider(providerId),
  });
}

export function useModelProviderDetailsQueries(providerIds: number[]) {
  const { models } = useApis();

  return useQueries({
    queries: providerIds.map((providerId) => ({
      enabled: providerId !== null,
      queryFn: () => models.getProvider(providerId),
      queryKey: modelQueryKeys.provider(providerId),
    })),
  });
}

import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type { ModelPresetKey } from '../api';
import { modelQueryKeys } from './model-provider.keys';

export function useModelInvocationsQuery(providerId: number | null, presetKey: ModelPresetKey | null = null) {
  const { models } = useApis();

  return useQuery({
    queryFn: () => models.listModelInvocations({ providerId, presetKey }),
    queryKey: modelQueryKeys.invocations(providerId, presetKey),
  });
}

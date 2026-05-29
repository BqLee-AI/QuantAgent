import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import { modelQueryKeys } from './model-provider.keys';

export function useModelPresetsQuery() {
  const { models } = useApis();

  return useQuery({
    queryFn: () => models.listModelPresets(),
    queryKey: modelQueryKeys.presets(),
  });
}

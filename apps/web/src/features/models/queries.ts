import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/shared/auth';

import {
  fetchModelConfig,
  fetchModelInvocations,
  saveModelConfig,
  testModelConnection,
  type SaveModelConfigInput,
} from './api';

export const modelQueryKeys = {
  all: ['models'] as const,
  config: () => [...modelQueryKeys.all, 'config'] as const,
  invocations: () => [...modelQueryKeys.all, 'invocations'] as const,
};

export function useModelConfigQuery() {
  const { apiClient } = useAuth();
  return useQuery({
    queryFn: () => fetchModelConfig(apiClient),
    queryKey: modelQueryKeys.config(),
  });
}

export function useModelInvocationsQuery() {
  const { apiClient } = useAuth();
  return useQuery({
    queryFn: () => fetchModelInvocations(apiClient),
    queryKey: modelQueryKeys.invocations(),
  });
}

export function useSaveModelConfigMutation() {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveModelConfigInput) => saveModelConfig(apiClient, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.config() });
    },
  });
}

export function useTestModelConnectionMutation() {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => testModelConnection(apiClient),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.config() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.invocations() });
    },
  });
}

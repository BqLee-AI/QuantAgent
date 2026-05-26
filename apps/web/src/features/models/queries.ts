import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '@/shared/auth';

import {
  createModelProvider,
  createProviderModel,
  deleteProviderModel,
  fetchModelInvocations,
  fetchModelPresets,
  fetchModelProvider,
  fetchModelProviders,
  setDefaultModelProvider,
  testModelProviderConnection,
  updateModelPreset,
  updateModelProvider,
  updateProviderModel,
  type CreateModelProviderInput,
  type ModelPresetKey,
  type SaveProviderModelInput,
  type UpdateModelPresetInput,
  type UpdateModelProviderInput,
} from './api';

export const modelQueryKeys = {
  all: ['models'] as const,
  providers: () => [...modelQueryKeys.all, 'providers'] as const,
  provider: (providerId: number | null) => [...modelQueryKeys.all, 'provider', providerId] as const,
  presets: () => [...modelQueryKeys.all, 'presets'] as const,
  invocations: (providerId: number | null, presetKey: ModelPresetKey | null) =>
    [...modelQueryKeys.all, 'invocations', providerId, presetKey] as const,
};

export function useModelProvidersQuery() {
  const { apiClient } = useAuth();
  return useQuery({
    queryFn: () => fetchModelProviders(apiClient),
    queryKey: modelQueryKeys.providers(),
  });
}

export function useModelProviderQuery(providerId: number | null) {
  const { apiClient } = useAuth();
  return useQuery({
    enabled: providerId !== null,
    queryFn: () => fetchModelProvider(apiClient, providerId as number),
    queryKey: modelQueryKeys.provider(providerId),
  });
}

export function useModelProviderDetailsQueries(providerIds: number[]) {
  const { apiClient } = useAuth();
  return useQueries({
    queries: providerIds.map((providerId) => ({
      enabled: providerId !== null,
      queryFn: () => fetchModelProvider(apiClient, providerId),
      queryKey: modelQueryKeys.provider(providerId),
    })),
  });
}

export function useModelPresetsQuery() {
  const { apiClient } = useAuth();
  return useQuery({
    queryFn: () => fetchModelPresets(apiClient),
    queryKey: modelQueryKeys.presets(),
  });
}

export function useModelInvocationsQuery(providerId: number | null, presetKey: ModelPresetKey | null = null) {
  const { apiClient } = useAuth();
  return useQuery({
    queryFn: () => fetchModelInvocations(apiClient, { providerId, presetKey }),
    queryKey: modelQueryKeys.invocations(providerId, presetKey),
  });
}

export function useCreateModelProviderMutation() {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateModelProviderInput) => createModelProvider(apiClient, input),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useUpdateModelProviderMutation(providerId: number | null) {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateModelProviderInput) => updateModelProvider(apiClient, providerId as number, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
    },
  });
}

export function useSetDefaultModelProviderMutation() {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (providerId: number) => setDefaultModelProvider(apiClient, providerId),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useTestModelProviderConnectionMutation(providerId: number | null) {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => testModelProviderConnection(apiClient, providerId as number),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.invocations(providerId, 'global_default') });
    },
  });
}

export function useCreateProviderModelMutation(providerId: number | null) {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveProviderModelInput) => createProviderModel(apiClient, providerId as number, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateProviderModelMutation(providerId: number | null) {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ input, modelId }: { input: SaveProviderModelInput; modelId: number }) =>
      updateProviderModel(apiClient, providerId as number, modelId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useDeleteProviderModelMutation(providerId: number | null) {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelId: number) => deleteProviderModel(apiClient, providerId as number, modelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateModelPresetMutation() {
  const { apiClient } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ input, presetKey }: { input: UpdateModelPresetInput; presetKey: ModelPresetKey }) =>
      updateModelPreset(apiClient, presetKey, input),
    onSuccess: (_preset, variables) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.invocations(null, variables.presetKey) });
    },
  });
}

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type {
  CreateModelProviderInput,
  ModelPresetKey,
  SaveProviderModelInput,
  UpdateModelPresetInput,
  UpdateModelProviderInput,
} from '../api';
import { modelQueryKeys } from '../queries/model-provider.keys';

export function useCreateModelProviderMutation() {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateModelProviderInput) => models.createProvider(input),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useUpdateModelProviderMutation(providerId: number | null) {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateModelProviderInput) => models.updateProvider(providerId as number, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
    },
  });
}

export function useDeleteModelProviderMutation(providerId: number | null) {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => models.deleteProvider(providerId as number),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useSetDefaultModelProviderMutation() {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: number) => models.setDefaultProvider(providerId),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useTestModelProviderConnectionMutation() {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: number) => models.testProviderConnection(providerId),
    onSettled: (_data, _error, providerId) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.invocations(providerId, null) });
    },
  });
}

export function useFetchRemoteProviderModelsMutation() {
  const { models } = useApis();

  return useMutation({
    mutationFn: (providerId: number) => models.listRemoteProviderModels(providerId),
  });
}

export function useCreateProviderModelMutation(providerId: number | null) {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: SaveProviderModelInput) => models.createProviderModel(providerId as number, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useCreateProviderModelForProviderMutation() {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, providerId }: { input: SaveProviderModelInput; providerId: number }) =>
      models.createProviderModel(providerId, input),
    onSuccess: (_model, variables) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(variables.providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateProviderModelMutation(providerId: number | null) {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, modelId }: { input: SaveProviderModelInput; modelId: number }) =>
      models.updateProviderModel(providerId as number, modelId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useDeleteProviderModelMutation(providerId: number | null) {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (modelId: number) => models.deleteProviderModel(providerId as number, modelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateModelPresetMutation() {
  const { models } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, presetKey }: { input: UpdateModelPresetInput; presetKey: ModelPresetKey }) =>
      models.updateModelPreset(presetKey, input),
    onSuccess: (_preset, variables) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.invocations(null, variables.presetKey) });
    },
  });
}

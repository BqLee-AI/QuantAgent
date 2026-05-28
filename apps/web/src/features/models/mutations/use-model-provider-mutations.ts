import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';

import type {
  CreateModelProviderInput,
  ModelPresetKey,
  SaveProviderModelInput,
  UpdateModelPresetInput,
  UpdateModelProviderInput,
} from '../api';
import { modelQueryKeys } from '../queries';
import { requireProviderId } from './provider-id';

export function useCreateModelProviderMutation() {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateModelProviderInput) => modelProviders.createProvider(input),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useUpdateModelProviderMutation(providerId: number | null) {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateModelProviderInput) =>
      modelProviders.updateProvider(requireProviderId(providerId), input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
    },
  });
}

export function useSetDefaultModelProviderMutation() {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: number) => modelProviders.setDefaultProvider(providerId),
    onSuccess: (provider) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(provider.id) });
    },
  });
}

export function useTestModelProviderConnectionMutation(providerId: number | null) {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => modelProviders.testProviderConnection(requireProviderId(providerId)),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({
        queryKey: modelQueryKeys.invocations(providerId, 'global_default'),
      });
    },
  });
}

export function useCreateProviderModelMutation(providerId: number | null) {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: SaveProviderModelInput) =>
      modelProviders.createProviderModel(requireProviderId(providerId), input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateProviderModelMutation(providerId: number | null) {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, modelId }: { input: SaveProviderModelInput; modelId: number }) =>
      modelProviders.updateProviderModel(requireProviderId(providerId), modelId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useDeleteProviderModelMutation(providerId: number | null) {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (modelId: number) =>
      modelProviders.deleteProviderModel(requireProviderId(providerId), modelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.providers() });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.provider(providerId) });
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
    },
  });
}

export function useUpdateModelPresetMutation() {
  const { modelProviders } = useApis();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ input, presetKey }: { input: UpdateModelPresetInput; presetKey: ModelPresetKey }) =>
      modelProviders.updatePreset(presetKey, input),
    onSuccess: (_preset, variables) => {
      void queryClient.invalidateQueries({ queryKey: modelQueryKeys.presets() });
      void queryClient.invalidateQueries({
        queryKey: modelQueryKeys.invocations(null, variables.presetKey),
      });
    },
  });
}

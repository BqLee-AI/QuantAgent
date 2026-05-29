import type { ModelPresetKey } from '../api';

export const modelQueryKeys = {
  all: ['models'] as const,
  providers: () => [...modelQueryKeys.all, 'providers'] as const,
  provider: (providerId: number | null) => [...modelQueryKeys.all, 'provider', providerId] as const,
  presets: () => [...modelQueryKeys.all, 'presets'] as const,
  invocations: (providerId: number | null, presetKey: ModelPresetKey | null) =>
    [...modelQueryKeys.all, 'invocations', providerId, presetKey] as const,
  remoteModels: (providerId: number | null) => [...modelQueryKeys.all, 'remote-models', providerId] as const,
};

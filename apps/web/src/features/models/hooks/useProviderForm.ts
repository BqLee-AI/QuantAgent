import { useEffect, useRef, useState, type FormEvent } from 'react';

import type {
  CreateModelProviderInput,
  ModelProviderDetail,
  SaveProviderModelInput,
  UpdateModelProviderInput,
} from '../api';
import type { ProviderPresetDefinition } from '../provider-presets';

interface UseProviderFormOptions {
  activePreset: ProviderPresetDefinition | undefined;
  createDraft?: {
    baseUrl: string;
    name: string;
  } | null;
  enabledOverride?: boolean;
  isCreating: boolean;
  provider: ModelProviderDetail | undefined;
  onCreateWithModel: (
    input: CreateModelProviderInput,
    model: SaveProviderModelInput | null,
  ) => Promise<ModelProviderDetail>;
  onSave: (input: UpdateModelProviderInput) => Promise<ModelProviderDetail>;
}

export function useProviderForm({
  activePreset,
  createDraft,
  enabledOverride,
  isCreating,
  provider,
  onCreateWithModel,
  onSave,
}: UseProviderFormOptions) {
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [enabled, setEnabled] = useState(false);
  const presetDraftName = activePreset?.draft.name ?? '';
  const presetDraftBaseUrl = activePreset?.draft.base_url ?? '';
  const lastProviderIdRef = useRef<number | null>(null);
  const lastPresetIdRef = useRef<string | null>(null);
  const lastProviderNameRef = useRef<string | null>(null);

  useEffect(() => {
    if (isCreating) return;
    if (!provider) return;
    const providerChanged = lastProviderIdRef.current !== provider.id;
    const providerNameChanged = lastProviderNameRef.current !== null && lastProviderNameRef.current !== provider.name;
    setName(provider.name);
    setBaseUrl(provider.base_url ?? '');
    setEnabled(provider.enabled);
    if (providerChanged && providerNameChanged) {
      setApiKey('');
    }
    lastProviderIdRef.current = provider.id;
    lastProviderNameRef.current = provider.name;
  }, [isCreating, provider]);

  useEffect(() => {
    if (typeof enabledOverride !== 'boolean') return;
    setEnabled(enabledOverride);
  }, [enabledOverride]);

  useEffect(() => {
    if (!isCreating) return;
    if (createDraft) {
      setName(createDraft.name);
      setBaseUrl(createDraft.baseUrl);
      setEnabled(false);
      setApiKey('');
      lastPresetIdRef.current = null;
      lastProviderNameRef.current = createDraft.name;
      return;
    }
    if (!activePreset) return;
    const presetChanged = lastPresetIdRef.current !== activePreset.id;
    setName(activePreset.draft.name);
    setBaseUrl(activePreset.draft.base_url ?? '');
    setEnabled(false);
    if (presetChanged) {
      setApiKey('');
      lastPresetIdRef.current = activePreset.id;
    }
    lastProviderNameRef.current = activePreset.draft.name;
  }, [activePreset, createDraft, isCreating]);

  function buildProviderInput(overrides: Partial<UpdateModelProviderInput> = {}): UpdateModelProviderInput {
    return {
      api_key: apiKey.trim() || null,
      base_url: baseUrl.trim() || null,
      enabled,
      name: name.trim(),
      provider_type: 'openai_compatible' as const,
      ...overrides,
    };
  }

  const providerInput = buildProviderInput();

  function isDirtyInput(input: UpdateModelProviderInput) {
    return (
      input.name !== (provider?.name ?? '') ||
      input.base_url !== (provider?.base_url ?? null) ||
      input.enabled !== provider?.enabled ||
      input.api_key !== null
    );
  }

  function canAutoCreateDraft(input: UpdateModelProviderInput) {
    return (
      input.api_key !== null ||
      input.enabled ||
      (input.base_url ?? '') !== presetDraftBaseUrl ||
      input.name !== presetDraftName
    );
  }

  async function persistProviderIfNeeded(options?: {
    forceCreate?: boolean;
    input?: UpdateModelProviderInput;
  }): Promise<ModelProviderDetail | true | false> {
    const nextInput = options?.input ?? providerInput;
    if (!nextInput.name) return false;
    try {
      if (isCreating) {
        if (!options?.forceCreate && !canAutoCreateDraft(nextInput)) {
          return true;
        }
        return await onCreateWithModel({ ...nextInput, is_default: false }, null);
      }
      if (!isDirtyInput(nextInput)) return true;
      return await onSave(nextInput);
    } catch {
      return false;
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void persistProviderIfNeeded();
  }

  return {
    apiKey,
    baseUrl,
    buildProviderInput,
    enabled,
    persistProviderIfNeeded,
    name,
    setApiKey,
    setBaseUrl,
    setEnabled,
    setName,
    submit,
  };
}

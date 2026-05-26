import type { ApiClient } from '@/shared/api';

export type ModelProviderType = 'openai_compatible';
export type ModelProviderStatus = 'configured' | 'missing_key' | 'disabled' | 'failed';
export type ModelProviderKeyStatus = 'configured' | 'missing';
export type ModelInvocationStatus = 'succeeded' | 'failed';
export type ModelPresetKey =
  | 'global_default'
  | 'economy_text'
  | 'general_text'
  | 'reasoning_text'
  | 'multimodal';
export type ModelPresetStatus = 'configured' | 'missing_primary' | 'invalid';

export interface ModelProviderModel {
  id: number;
  provider_id: number;
  model_name: string;
  enabled: boolean;
  supports_vision: boolean;
  is_global_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelProviderSummary {
  id: number;
  provider_type: ModelProviderType;
  name: string;
  base_url: string | null;
  enabled: boolean;
  is_default: boolean;
  status: ModelProviderStatus;
  key_status: ModelProviderKeyStatus;
  masked_key: string | null;
  last_error: string | null;
  model_count: number;
  updated_at: string;
}

export interface ModelProviderDetail extends ModelProviderSummary {
  models: ModelProviderModel[];
}

export interface ModelProviderList {
  default_provider_id: number | null;
  providers: ModelProviderSummary[];
}

export interface CreateModelProviderInput {
  provider_type: ModelProviderType;
  name: string;
  base_url?: string | null;
  api_key?: string | null;
  enabled: boolean;
  is_default: boolean;
}

export interface UpdateModelProviderInput {
  provider_type: ModelProviderType;
  name: string;
  base_url?: string | null;
  api_key?: string | null;
  enabled: boolean;
}

export interface SaveProviderModelInput {
  model_name: string;
  enabled: boolean;
  supports_vision: boolean;
  is_global_default: boolean;
}

export interface ModelPresetBinding {
  preset_key: ModelPresetKey;
  title: string;
  description: string;
  primary_model: ModelProviderModel | null;
  fallback_model: ModelProviderModel | null;
  status: ModelPresetStatus;
  validation_message: string | null;
}

export interface UpdateModelPresetInput {
  primary_model_id: number | null;
  fallback_model_id: number | null;
}

export interface ModelTokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface ModelInvocation {
  id: number | null;
  provider_id: number | null;
  provider_type: ModelProviderType;
  provider_name: string;
  model: string;
  preset_key: ModelPresetKey | null;
  status: ModelInvocationStatus;
  token_usage: ModelTokenUsage;
  error_summary: string | null;
  request_id: string | null;
  trace_id: string | null;
  agent_run_id: string | null;
  created_at: string;
}

export interface ModelTestConnectionResult {
  success: boolean;
  invocation: ModelInvocation;
}

export function fetchModelProviders(apiClient: ApiClient): Promise<ModelProviderList> {
  return apiClient.get<ModelProviderList>('/models/providers');
}

export function fetchModelProvider(apiClient: ApiClient, providerId: number): Promise<ModelProviderDetail> {
  return apiClient.get<ModelProviderDetail>(`/models/providers/${providerId}`);
}

export function createModelProvider(
  apiClient: ApiClient,
  input: CreateModelProviderInput,
): Promise<ModelProviderDetail> {
  return apiClient.post<CreateModelProviderInput, ModelProviderDetail>('/models/providers', input);
}

export function updateModelProvider(
  apiClient: ApiClient,
  providerId: number,
  input: UpdateModelProviderInput,
): Promise<ModelProviderDetail> {
  return apiClient.put<UpdateModelProviderInput, ModelProviderDetail>(`/models/providers/${providerId}`, input);
}

export function setDefaultModelProvider(
  apiClient: ApiClient,
  providerId: number,
): Promise<ModelProviderDetail> {
  return apiClient.post<Record<string, never>, ModelProviderDetail>(
    `/models/providers/${providerId}/actions/set-default`,
    {},
  );
}

export function testModelProviderConnection(
  apiClient: ApiClient,
  providerId: number,
): Promise<ModelTestConnectionResult> {
  return apiClient.post<Record<string, never>, ModelTestConnectionResult>(
    `/models/providers/${providerId}/actions/test-connection`,
    {},
  );
}

export function createProviderModel(
  apiClient: ApiClient,
  providerId: number,
  input: SaveProviderModelInput,
): Promise<ModelProviderModel> {
  return apiClient.post<SaveProviderModelInput, ModelProviderModel>(`/models/providers/${providerId}/models`, input);
}

export function updateProviderModel(
  apiClient: ApiClient,
  providerId: number,
  modelId: number,
  input: SaveProviderModelInput,
): Promise<ModelProviderModel> {
  return apiClient.put<SaveProviderModelInput, ModelProviderModel>(
    `/models/providers/${providerId}/models/${modelId}`,
    input,
  );
}

export function deleteProviderModel(
  apiClient: ApiClient,
  providerId: number,
  modelId: number,
): Promise<{ deleted: boolean }> {
  return apiClient.del<{ deleted: boolean }>(`/models/providers/${providerId}/models/${modelId}`);
}

export function fetchModelPresets(apiClient: ApiClient): Promise<ModelPresetBinding[]> {
  return apiClient.get<ModelPresetBinding[]>('/models/presets');
}

export function updateModelPreset(
  apiClient: ApiClient,
  presetKey: ModelPresetKey,
  input: UpdateModelPresetInput,
): Promise<ModelPresetBinding> {
  return apiClient.put<UpdateModelPresetInput, ModelPresetBinding>(`/models/presets/${presetKey}`, input);
}

export function fetchModelInvocations(
  apiClient: ApiClient,
  options: {
    providerId?: number | null;
    presetKey?: ModelPresetKey | null;
  } = {},
): Promise<ModelInvocation[]> {
  const searchParams = new URLSearchParams();
  if (options.providerId) {
    searchParams.set('provider_id', String(options.providerId));
  }
  if (options.presetKey) {
    searchParams.set('preset_key', options.presetKey);
  }
  const suffix = searchParams.size > 0 ? `?${searchParams.toString()}` : '';
  return apiClient.get<ModelInvocation[]>(`/models/invocations${suffix}`);
}

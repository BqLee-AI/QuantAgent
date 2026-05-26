import type { ApiClient } from '@/shared/api';

export type ModelProviderType = 'openai_compatible';
export type ModelConfigStatus = 'configured' | 'missing_key' | 'disabled' | 'failed';
export type ModelConfigKeyStatus = 'configured' | 'missing';
export type ModelInvocationStatus = 'succeeded' | 'failed';

export interface ModelConfig {
  provider_type: ModelProviderType;
  name: string;
  base_url: string | null;
  model: string;
  enabled: boolean;
  status: ModelConfigStatus;
  key_status: ModelConfigKeyStatus;
  masked_key: string | null;
  last_error: string | null;
  updated_at: string | null;
}

export interface SaveModelConfigInput {
  provider_type: ModelProviderType;
  name: string;
  base_url?: string | null;
  model: string;
  api_key?: string | null;
  enabled: boolean;
}

export interface ModelTokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface ModelInvocation {
  id: number | null;
  provider_type: ModelProviderType;
  provider_name: string;
  model: string;
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

export function fetchModelConfig(apiClient: ApiClient): Promise<ModelConfig> {
  return apiClient.get<ModelConfig>('/models/config');
}

export function saveModelConfig(
  apiClient: ApiClient,
  input: SaveModelConfigInput,
): Promise<ModelConfig> {
  return apiClient.put<SaveModelConfigInput, ModelConfig>('/models/config', input);
}

export function testModelConnection(
  apiClient: ApiClient,
): Promise<ModelTestConnectionResult> {
  return apiClient.post<Record<string, never>, ModelTestConnectionResult>(
    '/models/actions/test-connection',
    {},
  );
}

export function fetchModelInvocations(apiClient: ApiClient): Promise<ModelInvocation[]> {
  return apiClient.get<ModelInvocation[]>('/models/invocations');
}

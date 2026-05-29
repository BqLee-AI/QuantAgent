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

export interface RemoteProviderModel {
  id: string;
  owned_by: string | null;
  supports_vision: boolean | null;
}

export interface ModelProviderApiContract {
  listProviders(): Promise<ModelProviderList>;
  getProvider(providerId: number): Promise<ModelProviderDetail>;
  createProvider(input: CreateModelProviderInput): Promise<ModelProviderDetail>;
  updateProvider(providerId: number, input: UpdateModelProviderInput): Promise<ModelProviderDetail>;
  deleteProvider(providerId: number): Promise<{ deleted: boolean }>;
  setDefaultProvider(providerId: number): Promise<ModelProviderDetail>;
  testProviderConnection(providerId: number): Promise<ModelTestConnectionResult>;
  listRemoteProviderModels(providerId: number): Promise<RemoteProviderModel[]>;
  createProviderModel(providerId: number, input: SaveProviderModelInput): Promise<ModelProviderModel>;
  updateProviderModel(providerId: number, modelId: number, input: SaveProviderModelInput): Promise<ModelProviderModel>;
  deleteProviderModel(providerId: number, modelId: number): Promise<{ deleted: boolean }>;
  listModelPresets(): Promise<ModelPresetBinding[]>;
  updateModelPreset(presetKey: ModelPresetKey, input: UpdateModelPresetInput): Promise<ModelPresetBinding>;
  listModelInvocations(options?: {
    providerId?: number | null;
    presetKey?: ModelPresetKey | null;
  }): Promise<ModelInvocation[]>;
}

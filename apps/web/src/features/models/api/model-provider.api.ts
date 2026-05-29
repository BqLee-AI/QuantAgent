import { BaseApi, type ApiClient } from '@/shared/api';

import type {
  CreateModelProviderInput,
  ModelInvocation,
  ModelPresetBinding,
  ModelPresetKey,
  ModelProviderApiContract,
  ModelProviderDetail,
  ModelProviderList,
  ModelProviderModel,
  ModelTestConnectionResult,
  RemoteProviderModel,
  SaveProviderModelInput,
  UpdateModelPresetInput,
  UpdateModelProviderInput,
} from './model-provider.contracts';

export class ModelProviderApi extends BaseApi implements ModelProviderApiContract {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: '/models' });
  }

  listProviders(): Promise<ModelProviderList> {
    return this.get<ModelProviderList>('/providers');
  }

  getProvider(providerId: number): Promise<ModelProviderDetail> {
    return this.get<ModelProviderDetail>(`/providers/${providerId}`);
  }

  createProvider(input: CreateModelProviderInput): Promise<ModelProviderDetail> {
    return this.post<CreateModelProviderInput, ModelProviderDetail>('/providers', input);
  }

  updateProvider(providerId: number, input: UpdateModelProviderInput): Promise<ModelProviderDetail> {
    return this.put<UpdateModelProviderInput, ModelProviderDetail>(`/providers/${providerId}`, input);
  }

  deleteProvider(providerId: number): Promise<{ deleted: boolean }> {
    return this.del<{ deleted: boolean }>(`/providers/${providerId}`);
  }

  setDefaultProvider(providerId: number): Promise<ModelProviderDetail> {
    return this.post<Record<string, never>, ModelProviderDetail>(`/providers/${providerId}/actions/set-default`, {});
  }

  testProviderConnection(providerId: number): Promise<ModelTestConnectionResult> {
    return this.post<Record<string, never>, ModelTestConnectionResult>(
      `/providers/${providerId}/actions/test-connection`,
      {},
    );
  }

  listRemoteProviderModels(providerId: number): Promise<RemoteProviderModel[]> {
    return this.get<RemoteProviderModel[]>(`/providers/${providerId}/remote-models`);
  }

  createProviderModel(providerId: number, input: SaveProviderModelInput): Promise<ModelProviderModel> {
    return this.post<SaveProviderModelInput, ModelProviderModel>(`/providers/${providerId}/models`, input);
  }

  updateProviderModel(
    providerId: number,
    modelId: number,
    input: SaveProviderModelInput,
  ): Promise<ModelProviderModel> {
    return this.put<SaveProviderModelInput, ModelProviderModel>(`/providers/${providerId}/models/${modelId}`, input);
  }

  deleteProviderModel(providerId: number, modelId: number): Promise<{ deleted: boolean }> {
    return this.del<{ deleted: boolean }>(`/providers/${providerId}/models/${modelId}`);
  }

  listModelPresets(): Promise<ModelPresetBinding[]> {
    return this.get<ModelPresetBinding[]>('/presets');
  }

  updateModelPreset(presetKey: ModelPresetKey, input: UpdateModelPresetInput): Promise<ModelPresetBinding> {
    return this.put<UpdateModelPresetInput, ModelPresetBinding>(`/presets/${presetKey}`, input);
  }

  listModelInvocations(
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
    return this.get<ModelInvocation[]>(`/invocations${suffix}`);
  }
}

export function createModelProviderApi(apiClient: ApiClient): ModelProviderApi {
  return new ModelProviderApi(apiClient);
}

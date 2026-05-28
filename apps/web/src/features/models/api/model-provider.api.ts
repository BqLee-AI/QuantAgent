import { BaseApi, type ApiClient } from '@/shared/api';

import type {
  CreateModelProviderInput,
  ModelInvocation,
  ModelPresetBinding,
  ModelPresetKey,
  ModelProviderDetail,
  ModelProviderList,
  ModelProviderModel,
  ModelTestConnectionResult,
  SaveProviderModelInput,
  UpdateModelPresetInput,
  UpdateModelProviderInput,
} from './model-provider.contracts';

export class ModelProviderApi extends BaseApi {
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

  updateProvider(
    providerId: number,
    input: UpdateModelProviderInput,
  ): Promise<ModelProviderDetail> {
    return this.put<UpdateModelProviderInput, ModelProviderDetail>(
      `/providers/${providerId}`,
      input,
    );
  }

  setDefaultProvider(providerId: number): Promise<ModelProviderDetail> {
    return this.post<Record<string, never>, ModelProviderDetail>(
      `/providers/${providerId}/actions/set-default`,
      {},
    );
  }

  testProviderConnection(providerId: number): Promise<ModelTestConnectionResult> {
    return this.post<Record<string, never>, ModelTestConnectionResult>(
      `/providers/${providerId}/actions/test-connection`,
      {},
    );
  }

  createProviderModel(
    providerId: number,
    input: SaveProviderModelInput,
  ): Promise<ModelProviderModel> {
    return this.post<SaveProviderModelInput, ModelProviderModel>(
      `/providers/${providerId}/models`,
      input,
    );
  }

  updateProviderModel(
    providerId: number,
    modelId: number,
    input: SaveProviderModelInput,
  ): Promise<ModelProviderModel> {
    return this.put<SaveProviderModelInput, ModelProviderModel>(
      `/providers/${providerId}/models/${modelId}`,
      input,
    );
  }

  deleteProviderModel(providerId: number, modelId: number): Promise<{ deleted: boolean }> {
    return this.del<{ deleted: boolean }>(`/providers/${providerId}/models/${modelId}`);
  }

  listPresets(): Promise<ModelPresetBinding[]> {
    return this.get<ModelPresetBinding[]>('/presets');
  }

  updatePreset(
    presetKey: ModelPresetKey,
    input: UpdateModelPresetInput,
  ): Promise<ModelPresetBinding> {
    return this.put<UpdateModelPresetInput, ModelPresetBinding>(
      `/presets/${presetKey}`,
      input,
    );
  }

  listInvocations(
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

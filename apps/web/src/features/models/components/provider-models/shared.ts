import type { ModelProviderModel } from '../../api';

export interface ProviderCatalogModel {
  id: string;
  name: string;
  supportsVision: boolean;
}

export function existingModelMap(models: ModelProviderModel[]) {
  return new Map(models.map((model) => [model.model_name.toLowerCase(), model]));
}

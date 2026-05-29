import type { ModelProviderSummary } from '../api';

export interface ProviderListItem {
  kind: 'create' | 'preset' | 'provider';
  providerId: number | null;
  presetId: string;
  name: string;
  isConfigured: boolean;
  summary?: ModelProviderSummary;
}

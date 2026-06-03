import { BaseApi, type ApiClient } from '@/shared/api';

import type {
  RuntimeAuditApiContract,
  RuntimeAuditNewsListResponse,
  RuntimeAuditQueryParams,
} from './runtime-audit.contracts';

export class RuntimeAuditApi extends BaseApi implements RuntimeAuditApiContract {
  constructor(apiClient: ApiClient) {
    super(apiClient, { basePath: '/runtime/audit' });
  }

  listAuditNews(params: RuntimeAuditQueryParams = {}): Promise<RuntimeAuditNewsListResponse> {
    return this.get<RuntimeAuditNewsListResponse>('/news', { params: { ...params } });
  }
}

export function createRuntimeAuditApi(apiClient: ApiClient): RuntimeAuditApi {
  return new RuntimeAuditApi(apiClient);
}

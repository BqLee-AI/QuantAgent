import type { ApiClient } from '@/shared/api';

import {
  createRuntimeAuditFixtureResponse,
  filterRuntimeAuditFixtureResponse,
} from '../utils/runtime-audit-fixtures';
import type {
  RuntimeAuditMessagesResponse,
  RuntimeAuditQueryParams,
} from './runtime-audit.contracts';

export class RuntimeAuditApi {
  // 当前 V1 只提供受控 fixture read model，用于验证审计流形态；不要伪装成生产 endpoint。
  constructor(_apiClient: ApiClient) {}

  async listAuditMessages(
    params: RuntimeAuditQueryParams = {},
  ): Promise<RuntimeAuditMessagesResponse> {
    return filterRuntimeAuditFixtureResponse(createRuntimeAuditFixtureResponse(), params);
  }
}

export function createRuntimeAuditApi(apiClient: ApiClient): RuntimeAuditApi {
  return new RuntimeAuditApi(apiClient);
}

import type {
  RuntimeAuditNewsListResponse,
  RuntimeAuditQueryParams,
} from '../types';

export interface RuntimeAuditApiContract {
  listAuditNews(params?: RuntimeAuditQueryParams): Promise<RuntimeAuditNewsListResponse>;
}

export type {
  RuntimeAuditNewsListResponse,
  RuntimeAuditQueryParams,
};

import type {
  RuntimeAuditMessagesResponse,
  RuntimeAuditQueryParams,
} from '../types';

export interface RuntimeAuditApiContract {
  listAuditMessages(params?: RuntimeAuditQueryParams): Promise<RuntimeAuditMessagesResponse>;
}

export type {
  RuntimeAuditMessagesResponse,
  RuntimeAuditQueryParams,
};

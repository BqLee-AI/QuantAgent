import { ApiError } from '@/shared/api';

export function formatModelApiError(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }

  if (!error.requestId) {
    return error.msg;
  }

  return `${error.msg}（Request ID: ${error.requestId}）`;
}

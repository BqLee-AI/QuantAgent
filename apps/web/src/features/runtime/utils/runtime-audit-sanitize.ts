import type { RuntimeAuditSafeValue } from '../types';

const blockedKeys = [
  'api_key',
  'chain_of_thought',
  'connection_string',
  'cookie',
  'password',
  'prompt',
  'provider_raw_response',
  'raw_article_body',
  'raw_prompt',
  'secret',
  'token',
];

export function isUnsafeRuntimeAuditKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return blockedKeys.some((blocked) => normalized.includes(blocked));
}

export function sanitizeRuntimeAuditDetails(
  value: Record<string, RuntimeAuditSafeValue> | null,
): Record<string, RuntimeAuditSafeValue> | null {
  if (!value) return null;
  return sanitizeObject(value);
}

function sanitizeObject(
  value: Record<string, RuntimeAuditSafeValue>,
): Record<string, RuntimeAuditSafeValue> {
  const sanitized: Record<string, RuntimeAuditSafeValue> = {};
  for (const [key, child] of Object.entries(value)) {
    sanitized[key] = isUnsafeRuntimeAuditKey(key) ? '[已脱敏]' : sanitizeValue(child);
  }
  return sanitized;
}

function sanitizeValue(value: RuntimeAuditSafeValue): RuntimeAuditSafeValue {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeValue(item));
  }
  if (value && typeof value === 'object') {
    return sanitizeObject(value);
  }
  return value;
}

import type { AgentAuditSafeValue } from '../types';

const blockedKeyFragments = [
  'api_key',
  'article_body',
  'chain_of_thought',
  'connection_string',
  'cookie',
  'password',
  'prompt',
  'provider_raw_response',
  'raw_article',
  'raw_payload',
  'raw_prompt',
  'secret',
  'token',
];

export function isUnsafeAgentAuditKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return blockedKeyFragments.some((blocked) => normalized.includes(blocked));
}

export function sanitizeAgentAuditJson(
  value: Record<string, AgentAuditSafeValue> | null | undefined,
): Record<string, AgentAuditSafeValue> | null {
  if (!value) return null;
  return sanitizeObject(value);
}

function sanitizeObject(value: Record<string, AgentAuditSafeValue>): Record<string, AgentAuditSafeValue> {
  const sanitized: Record<string, AgentAuditSafeValue> = {};
  for (const [key, child] of Object.entries(value)) {
    sanitized[key] = isUnsafeAgentAuditKey(key) ? '[已脱敏]' : sanitizeValue(child);
  }
  return sanitized;
}

function sanitizeValue(value: AgentAuditSafeValue): AgentAuditSafeValue {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeValue(item));
  }
  if (value && typeof value === 'object') {
    return sanitizeObject(value);
  }
  return value;
}

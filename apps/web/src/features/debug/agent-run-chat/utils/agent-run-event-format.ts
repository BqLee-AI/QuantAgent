import type { AgentDebugSseEvent } from '../api';
import type { AgentRunTodoItem } from '../types';

const SENSITIVE_PATTERN = /\b(secret|token|api[_-]?key|authorization|cookie|prompt|raw_response|traceback|sk-[a-z0-9_-]+)\b/iu;

export function safeEventSummary(event: AgentDebugSseEvent): string {
  const summary = event.safe_summary?.trim() || fallbackSummary(event);
  return safeDisplayText(summary);
}

export function safeDisplayText(value: string): string {
  if (!SENSITIVE_PATTERN.test(value)) {
    return value;
  }
  return '[已脱敏摘要]';
}

export function fallbackSummary(event: AgentDebugSseEvent): string {
  return `收到 ${event.type} 事件。`;
}

export function readStringPayload(event: AgentDebugSseEvent, key: string): string | null {
  const value = event.payload[key];
  return typeof value === 'string' && value.trim() ? safeDisplayText(value.trim()) : null;
}

export function readTodos(event: AgentDebugSseEvent): AgentRunTodoItem[] {
  const value = event.payload.todos;
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null;
      const record = item as Record<string, unknown>;
      const content = typeof record.content === 'string' ? record.content : String(record.title ?? '');
      const status = typeof record.status === 'string' ? record.status : 'pending';
      return content ? {
        content: safeDisplayText(content),
        status: safeDisplayText(status),
      } satisfies AgentRunTodoItem : null;
    })
    .filter((item): item is AgentRunTodoItem => item !== null);
}

export function formatEventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'artifact.created': 'Artifact',
    'model.delta': '模型输出',
    'run.completed': '运行完成',
    'run.failed': '运行失败',
    'run.output': '最终输出',
    'run.started': '运行开始',
    'subagent.completed': 'SubAgent 完成',
    'subagent.started': 'SubAgent 启动',
    'todo.updated': 'Todo 更新',
    'tool.completed': '工具完成',
    'tool.failed': '工具失败',
    'tool.started': '工具启动',
  };
  return labels[type] ?? type;
}

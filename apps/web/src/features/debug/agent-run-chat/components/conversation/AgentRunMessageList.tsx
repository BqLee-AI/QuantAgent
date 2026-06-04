import type { AgentRunChatMessage } from '../../types';
import { AgentRunMessageBubble } from './AgentRunMessageBubble';

export function AgentRunMessageList({ messages }: { messages: readonly AgentRunChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-hairline bg-canvas px-5 py-8 text-center text-[13px] text-muted">
        选择 fixture 后启动运行，消息流会按 AgentRunEvent 实时追加。
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {messages.map((message) => (
        <AgentRunMessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}

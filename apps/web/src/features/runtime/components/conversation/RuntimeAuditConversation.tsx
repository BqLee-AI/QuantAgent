import type {
  RuntimeAuditMessage,
  RuntimeAuditMessageGroup,
} from '../../types';
import { RuntimeAuditEmptyState } from '../states/RuntimeAuditEmptyState';
import { RuntimeAuditMessageGroup as RuntimeAuditMessageGroupItem } from './RuntimeAuditMessageGroup';

interface RuntimeAuditConversationProps {
  groups: readonly RuntimeAuditMessageGroup[];
  messages: readonly RuntimeAuditMessage[];
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
}

export function RuntimeAuditConversation({
  groups,
  messages,
  selectedMessageId,
  onSelectMessage,
}: RuntimeAuditConversationProps) {
  if (groups.length === 0) {
    return <RuntimeAuditEmptyState />;
  }

  return (
    <div className="grid gap-4">
      {groups.map((group) => (
        <RuntimeAuditMessageGroupItem
          key={group.group_id}
          group={group}
          messages={messages.filter((message) => message.group_id === group.group_id)}
          selectedMessageId={selectedMessageId}
          onSelectMessage={onSelectMessage}
        />
      ))}
    </div>
  );
}

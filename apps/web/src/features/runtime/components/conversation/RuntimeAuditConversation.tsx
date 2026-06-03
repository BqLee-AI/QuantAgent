import type { RuntimeAuditNewsItem } from '../../types';
import { RuntimeAuditEmptyState } from '../states/RuntimeAuditEmptyState';
import { RuntimeAuditMessage as RuntimeAuditNewsListItem } from './RuntimeAuditMessage';

interface RuntimeAuditConversationProps {
  items: readonly RuntimeAuditNewsItem[];
  selectedRawEventId: string | null;
  onSelectNews: (rawEventId: string) => void;
}

export function RuntimeAuditConversation({
  items,
  selectedRawEventId,
  onSelectNews,
}: RuntimeAuditConversationProps) {
  if (items.length === 0) {
    return <RuntimeAuditEmptyState />;
  }

  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <RuntimeAuditNewsListItem
          key={item.raw_event_id}
          isSelected={selectedRawEventId === item.raw_event_id}
          item={item}
          onSelect={onSelectNews}
        />
      ))}
    </div>
  );
}

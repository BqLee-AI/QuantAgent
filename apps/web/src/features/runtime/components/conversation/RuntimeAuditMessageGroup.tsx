import type {
  RuntimeAuditMessage,
  RuntimeAuditMessageGroup as RuntimeAuditMessageGroupModel,
} from '../../types';
import { formatRuntimeAuditDecision } from '../../utils';
import { RuntimeAuditMessage as RuntimeAuditMessageItem } from './RuntimeAuditMessage';

interface RuntimeAuditMessageGroupProps {
  group: RuntimeAuditMessageGroupModel;
  messages: readonly RuntimeAuditMessage[];
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
}

export function RuntimeAuditMessageGroup({
  group,
  messages,
  selectedMessageId,
  onSelectMessage,
}: RuntimeAuditMessageGroupProps) {
  return (
    <section className="grid gap-3 rounded-xl border border-hairline bg-surface-soft p-3">
      <div className="flex flex-col gap-1 px-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="m-0 text-[15px] font-semibold text-ink">{group.source_title}</h2>
          {group.decision ? (
            <span className="rounded-full bg-canvas px-2.5 py-1 text-[12px] font-semibold text-muted-strong">
              {formatRuntimeAuditDecision(group.decision)}
            </span>
          ) : null}
        </div>
        <p className="m-0 text-body-sm text-muted">{group.summary}</p>
      </div>
      <div className="grid gap-2">
        {messages.map((message) => (
          <RuntimeAuditMessageItem
            key={message.id}
            isSelected={selectedMessageId === message.id}
            message={message}
            onSelect={onSelectMessage}
          />
        ))}
      </div>
    </section>
  );
}

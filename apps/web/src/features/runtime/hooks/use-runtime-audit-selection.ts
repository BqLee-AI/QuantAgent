import { useEffect, useMemo, useState } from 'react';

import type { RuntimeAuditMessage, RuntimeAuditMessageGroup } from '../types';

export function useRuntimeAuditSelection(
  groups: readonly RuntimeAuditMessageGroup[],
  messages: readonly RuntimeAuditMessage[],
) {
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedMessageId && messages.some((message) => message.id === selectedMessageId)) {
      return;
    }
    setSelectedMessageId(messages[0]?.id ?? null);
  }, [messages, selectedMessageId]);

  const selectedMessage = useMemo(
    () => messages.find((message) => message.id === selectedMessageId) ?? null,
    [messages, selectedMessageId],
  );

  const selectedGroup = useMemo(
    () => groups.find((group) => group.group_id === selectedMessage?.group_id) ?? null,
    [groups, selectedMessage?.group_id],
  );

  return {
    selectedGroup,
    selectedMessage,
    selectedMessageId,
    setSelectedMessageId,
  };
}

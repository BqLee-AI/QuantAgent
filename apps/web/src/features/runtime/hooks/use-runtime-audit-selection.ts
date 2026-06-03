import { useEffect, useMemo, useState } from 'react';

import type { RuntimeAuditNewsItem } from '../types';

export function useRuntimeAuditSelection(items: readonly RuntimeAuditNewsItem[]) {
  const [selectedRawEventId, setSelectedRawEventId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedRawEventId && items.some((item) => item.raw_event_id === selectedRawEventId)) {
      return;
    }
    setSelectedRawEventId(items[0]?.raw_event_id ?? null);
  }, [items, selectedRawEventId]);

  const selectedNews = useMemo(
    () => items.find((item) => item.raw_event_id === selectedRawEventId) ?? null,
    [items, selectedRawEventId],
  );

  return {
    selectedNews,
    selectedRawEventId,
    setSelectedRawEventId,
  };
}

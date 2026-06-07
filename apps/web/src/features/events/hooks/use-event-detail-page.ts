import { useState } from 'react';

import type { EventAgentStage } from '../types';
import { useEventDetailQuery, useEventRouterOutputQuery } from '../queries';

export function useEventDetailPage(rawEventId: string) {
  const detailQuery = useEventDetailQuery(rawEventId);
  const [selectedAgentStage, setSelectedAgentStage] = useState<EventAgentStage | null>(null);
  const routerOutputQuery = useEventRouterOutputQuery(
    rawEventId,
    selectedAgentStage?.routed_event_id,
    Boolean(selectedAgentStage?.has_output_json),
  );

  return {
    detailQuery,
    routerOutputQuery,
    selectedAgentStage,
    setSelectedAgentStage,
  };
}

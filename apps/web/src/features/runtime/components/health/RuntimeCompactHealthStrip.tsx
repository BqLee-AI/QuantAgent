import { Button, Chip } from '@heroui/react';

import type { RuntimeAuditHealthSummary } from '../../types';
import { formatRuntimeAuditDate } from '../../utils';

interface RuntimeCompactHealthStripProps {
  health: RuntimeAuditHealthSummary | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function RuntimeCompactHealthStrip({
  health,
  isRefreshing,
  onRefresh,
}: RuntimeCompactHealthStripProps) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-hairline bg-canvas px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          {health?.status ?? 'unknown'}
        </Chip>
        <span className="text-body-sm text-muted">
          {health ? `${health.total_items} 篇新闻 · ${formatRuntimeAuditDate(health.generated_at)}` : '尚未读取'}
        </span>
      </div>
      <Button isDisabled={isRefreshing} size="sm" type="button" variant="outline" onPress={onRefresh}>
        {isRefreshing ? '刷新中...' : '刷新'}
      </Button>
    </section>
  );
}

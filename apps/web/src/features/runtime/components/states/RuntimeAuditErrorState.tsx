import { Button } from '@heroui/react';

import { formatRuntimeAuditErrorMeta } from '../../utils/runtime-audit-error';

interface RuntimeAuditErrorStateProps {
  error: unknown;
  onRetry: () => void;
}

export function RuntimeAuditErrorState({ error, onRetry }: RuntimeAuditErrorStateProps) {
  const message = error instanceof Error ? error.message : '未知错误';
  const meta = formatRuntimeAuditErrorMeta(error);

  return (
    <div className="rounded-lg border border-trading-down/25 bg-trading-down/6 px-4 py-4">
      <p className="m-0 text-body-sm font-semibold text-trading-down">审计流读取失败</p>
      <p className="m-0 mt-1 text-body-sm text-muted-strong">{message}</p>
      {meta ? <p className="m-0 mt-2 text-caption text-muted">{meta}</p> : null}
      <Button className="mt-3" size="sm" type="button" variant="outline" onPress={onRetry}>
        重新读取
      </Button>
    </div>
  );
}

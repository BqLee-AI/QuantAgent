import { Button } from "@heroui/react";

import { formatRuntimeApiError, isPermissionDeniedError } from "../../utils";

interface RuntimePanelStateProps {
  error?: unknown;
  isLoading?: boolean;
  loadingLabel?: string;
  emptyLabel?: string;
  unavailableLabel?: string | null;
  onRetry?: () => void;
}

export function RuntimePanelState({
  emptyLabel = "暂无运行态数据。",
  error,
  isLoading = false,
  loadingLabel = "正在读取 REST 快照...",
  onRetry,
  unavailableLabel,
}: RuntimePanelStateProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-5 text-sm text-muted">
        {loadingLabel}
      </div>
    );
  }

  if (error) {
    const isForbidden = isPermissionDeniedError(error);
    return (
      <div className="rounded-lg border border-danger/20 bg-danger/6 px-4 py-4">
        <p className="m-0 text-sm font-semibold text-danger">
          {isForbidden ? "权限不足，无法读取该运行态资源。" : "读取失败"}
        </p>
        <p className="m-0 mt-1 text-sm text-muted-strong">{formatRuntimeApiError(error)}</p>
        {onRetry ? (
          <Button className="mt-3" size="sm" type="button" variant="outline" onPress={onRetry}>
            重新读取
          </Button>
        ) : null}
      </div>
    );
  }

  if (unavailableLabel) {
    return (
      <div className="rounded-lg border border-warning/25 bg-warning/8 px-4 py-4">
        <p className="m-0 text-sm font-semibold text-warning">局部资源暂不可用</p>
        <p className="m-0 mt-1 text-sm text-muted-strong">{unavailableLabel}</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-hairline bg-surface-soft px-4 py-5 text-sm text-muted">
      {emptyLabel}
    </div>
  );
}

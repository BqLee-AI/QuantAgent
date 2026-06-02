import { formatRuntimeAuditErrorMeta } from '../../utils/runtime-audit-error';

interface RuntimeAuditPermissionStateProps {
  error: unknown;
}

export function RuntimeAuditPermissionState({ error }: RuntimeAuditPermissionStateProps) {
  const meta = formatRuntimeAuditErrorMeta(error);

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-4 text-body-sm text-amber-700">
      <p className="m-0 font-semibold">权限不足，无法读取 Runtime 审计流。</p>
      <p className="m-0 mt-1">请检查当前会话 capability 或后端权限配置。</p>
      {meta ? <p className="m-0 mt-2 text-caption text-amber-800">{meta}</p> : null}
    </div>
  );
}

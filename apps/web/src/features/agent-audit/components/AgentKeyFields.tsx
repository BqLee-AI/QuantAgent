import type { AgentAuditKeyFields } from '../types';
import {
  formatAgentAuditFieldValue,
  getAgentAuditKeyFieldDescription,
  getAgentAuditKeyFieldLabel,
  getAgentAuditKeyFieldState,
  getAgentAuditKeyFieldValue,
} from '../utils';

interface AgentKeyFieldsProps {
  fields: AgentAuditKeyFields;
}

export function AgentKeyFields({ fields }: AgentKeyFieldsProps) {
  const entries = Object.entries(fields).filter(([, field]) => field !== undefined);

  if (entries.length === 0) {
    return (
      <p className="m-0 rounded-lg border border-hairline bg-surface-soft px-3 py-2 text-body-sm text-muted">
        当前阶段没有可展示的关键字段。
      </p>
    );
  }

  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {entries.map(([key, field]) => {
        const state = getAgentAuditKeyFieldState(field);
        const description = getAgentAuditKeyFieldDescription(field);
        return (
          <div key={key} className="rounded-lg border border-hairline bg-surface-soft px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-normal text-muted">
              {getAgentAuditKeyFieldLabel(key, field)}
            </dt>
            <dd className="m-0 mt-1 break-words text-body-sm font-semibold text-ink">
              {state === 'masked' ? '已脱敏' : formatAgentAuditFieldValue(getAgentAuditKeyFieldValue(field))}
            </dd>
            {state === 'unavailable' || description ? (
              <p className="m-0 mt-1 text-[12px] text-muted">
                {description ?? '后端未返回该字段。'}
              </p>
            ) : null}
          </div>
        );
      })}
    </dl>
  );
}

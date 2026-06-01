import { Button, Input, Label, TextField } from "@heroui/react";
import type { FormEvent } from "react";

import type { RuntimeDashboardFilterDraft } from "../../types";

interface RuntimeDashboardFiltersProps {
  draft: RuntimeDashboardFilterDraft;
  onApply: () => void;
  onReset: () => void;
  onUpdate: (nextDraft: Partial<RuntimeDashboardFilterDraft>) => void;
}

export function RuntimeDashboardFilters({
  draft,
  onApply,
  onReset,
  onUpdate,
}: RuntimeDashboardFiltersProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  return (
    <form className="rounded-xl border border-hairline bg-canvas p-4" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="event_id"
          value={draft.eventId}
          onChange={(value) => onUpdate({ eventId: value })}
        >
          <Label className="text-[13px] font-medium text-ink">event_id</Label>
          <Input placeholder="evt_..." variant="primary" />
        </TextField>
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="trace_id"
          value={draft.traceId}
          onChange={(value) => onUpdate({ traceId: value })}
        >
          <Label className="text-[13px] font-medium text-ink">trace_id</Label>
          <Input placeholder="trace_..." variant="primary" />
        </TextField>
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="plugin_id"
          value={draft.pluginId}
          onChange={(value) => onUpdate({ pluginId: value })}
        >
          <Label className="text-[13px] font-medium text-ink">plugin_id</Label>
          <Input placeholder="plugin id" variant="primary" />
        </TextField>
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="status"
          value={draft.status}
          onChange={(value) => onUpdate({ status: value })}
        >
          <Label className="text-[13px] font-medium text-ink">status</Label>
          <Input placeholder="running / failed" variant="primary" />
        </TextField>
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="time_from"
          value={draft.timeFrom}
          onChange={(value) => onUpdate({ timeFrom: value })}
        >
          <Label className="text-[13px] font-medium text-ink">time_from</Label>
          <Input placeholder="2026-06-01T00:00:00Z" variant="primary" />
        </TextField>
        <TextField
          className="grid gap-2 xl:col-span-1"
          name="time_to"
          value={draft.timeTo}
          onChange={(value) => onUpdate({ timeTo: value })}
        >
          <Label className="text-[13px] font-medium text-ink">time_to</Label>
          <Input placeholder="2026-06-02T00:00:00Z" variant="primary" />
        </TextField>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="m-0 text-xs text-muted">
          REST 快照是真源；实时通道只作为刷新提示。筛选失败会显示在对应资源面板内。
        </p>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onPress={onReset}>
            重置
          </Button>
          <Button type="submit" variant="primary">
            应用筛选
          </Button>
        </div>
      </div>
    </form>
  );
}

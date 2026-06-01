import { createFileRoute } from "@tanstack/react-router";

import { RuntimeDashboardPage } from "../../../../features/runtime";
import type { RuntimeDashboardFilters } from "../../../../features/runtime";

export const Route = createFileRoute("/_app/(workspace)/runtime/")({
  validateSearch: (search: Record<string, unknown>): Partial<RuntimeDashboardFilters> => ({
    event_id: typeof search.event_id === "string" ? search.event_id : undefined,
    page: typeof search.page === "number" ? search.page : Number(search.page ?? 1),
    page_size:
      typeof search.page_size === "number" ? search.page_size : Number(search.page_size ?? 10),
    plugin_id: typeof search.plugin_id === "string" ? search.plugin_id : undefined,
    status: typeof search.status === "string" ? search.status : undefined,
    time_from: typeof search.time_from === "string" ? search.time_from : undefined,
    time_to: typeof search.time_to === "string" ? search.time_to : undefined,
    trace_id: typeof search.trace_id === "string" ? search.trace_id : undefined,
  }),
  component: RuntimePage,
});

function RuntimePage() {
  const search = Route.useSearch();

  return <RuntimeDashboardPage search={search} />;
}

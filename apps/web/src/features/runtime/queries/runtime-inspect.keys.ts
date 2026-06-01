import type { RuntimeDashboardFilters } from "../types/runtime-dashboard.types";

export const runtimeInspectKeys = {
  all: ["runtime-inspect"] as const,
  health: () => [...runtimeInspectKeys.all, "health"] as const,
  agentRuns: (filters: RuntimeDashboardFilters) =>
    [...runtimeInspectKeys.all, "agent-runs", filters] as const,
  toolInvocations: (filters: RuntimeDashboardFilters) =>
    [...runtimeInspectKeys.all, "tool-invocations", filters] as const,
  schedulerRuns: (filters: RuntimeDashboardFilters) =>
    [...runtimeInspectKeys.all, "scheduler-runs", filters] as const,
  runtimeErrors: (filters: RuntimeDashboardFilters) =>
    [...runtimeInspectKeys.all, "runtime-errors", filters] as const,
};

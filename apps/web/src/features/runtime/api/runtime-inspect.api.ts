import { BaseApi, type ApiClient, type RequestConfig } from "@/shared/api";

import type {
  AgentRunSummary,
  RuntimeErrorSummary,
  RuntimeErrorsListParams,
  RuntimeHealthSummary,
  RuntimeInspectApiContract,
  RuntimeInspectListParams,
  RuntimeListResponse,
  SchedulerRunsListParams,
  SchedulerRunSummary,
  ToolInvocationSummary,
} from "./runtime-inspect.contracts";

function cleanParams(params: RuntimeInspectListParams = {}): RequestConfig["params"] {
  const next: RequestConfig["params"] = {};

  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    next[key] = value;
  }

  return next;
}

export class RuntimeInspectApi extends BaseApi implements RuntimeInspectApiContract {
  constructor(apiClient: ApiClient) {
    super(apiClient);
  }

  getHealth(): Promise<RuntimeHealthSummary> {
    return this.get<RuntimeHealthSummary>("/runtime/health");
  }

  listAgentRuns(
    params: RuntimeInspectListParams = {},
  ): Promise<RuntimeListResponse<AgentRunSummary>> {
    return this.get<RuntimeListResponse<AgentRunSummary>>("/agents/runs", {
      params: cleanParams(params),
    });
  }

  listToolInvocations(
    params: RuntimeInspectListParams = {},
  ): Promise<RuntimeListResponse<ToolInvocationSummary>> {
    return this.get<RuntimeListResponse<ToolInvocationSummary>>("/tools/invocations", {
      params: cleanParams(params),
    });
  }

  listSchedulerRuns(
    params: SchedulerRunsListParams = {},
  ): Promise<RuntimeListResponse<SchedulerRunSummary>> {
    return this.get<RuntimeListResponse<SchedulerRunSummary>>("/scheduler-runs", {
      params: cleanParams(params),
    });
  }

  listRuntimeErrors(
    params: RuntimeErrorsListParams = {},
  ): Promise<RuntimeListResponse<RuntimeErrorSummary>> {
    return this.get<RuntimeListResponse<RuntimeErrorSummary>>("/runtime/errors", {
      params: cleanParams(params),
    });
  }
}

export function createRuntimeInspectApi(apiClient: ApiClient): RuntimeInspectApi {
  return new RuntimeInspectApi(apiClient);
}

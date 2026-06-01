## ADDED Requirements

### Requirement: Runtime Inspect V1 使用按对象拆分的只读资源

Runtime Inspect V1 SHALL expose dedicated read resources for runtime objects instead of a single mixed dashboard endpoint.

#### Scenario: Runtime health 使用独立资源
- **WHEN** a client needs runtime health summary
- **THEN** it queries `GET /api/v1/runtime/health`
- **AND** the response uses the standard API envelope
- **AND** the resource returns structured summary data instead of raw probe internals

#### Scenario: AgentRun、ToolInvocation、SchedulerRun 和 RuntimeError 使用独立资源
- **WHEN** a client needs runtime inspect data
- **THEN** AgentRun uses `GET /api/v1/agents/runs` and `GET /api/v1/agents/runs/{run_id}`
- **AND** ToolInvocation uses `GET /api/v1/tools/invocations` and `GET /api/v1/tools/invocations/{invocation_id}`
- **AND** SchedulerRun uses `GET /api/v1/scheduler-runs` and `GET /api/v1/scheduler-runs/{run_id}`
- **AND** RuntimeError uses `GET /api/v1/runtime/errors` and `GET /api/v1/runtime/errors/{error_id}`
- **AND** Runtime Inspect V1 does not require a catch-all `/api/v1/runtime/inspect` endpoint

### Requirement: Runtime Inspect V1 定义共享过滤和稳定关联字段

Runtime Inspect V1 SHALL define shared filters and stable tracking fields across runtime read resources.

#### Scenario: shared filters support event and trace investigation
- **WHEN** a client lists runtime objects for investigation
- **THEN** list resources support shared filters where applicable
- **AND** shared filters include `event_id`
- **AND** shared filters include `trace_id`
- **AND** shared filters include `plugin_id`
- **AND** shared filters include `status`
- **AND** shared filters include `time_from` and `time_to`

#### Scenario: shared tracking fields stay stable across resources
- **WHEN** runtime objects reference the same execution chain
- **THEN** Runtime Inspect uses stable field names for `event_id`, `trace_id`, `request_id` and `correlation_id`
- **AND** tool invocations can reference `agent_run_id`
- **AND** scheduler-triggered objects can reference `scheduler_run_id`
- **AND** SchedulerRun field naming in Runtime Inspect does not diverge from its future dedicated contract

### Requirement: Runtime Inspect V1 为每类对象提供 summary/detail DTO

Runtime Inspect V1 SHALL expose minimum summary and detail shapes for each runtime object family.

#### Scenario: Runtime health exposes structured summary
- **WHEN** `GET /api/v1/runtime/health` succeeds
- **THEN** the response includes active run counts, recent failure counts, runtime error severity summary, backend status summary and `generated_at`
- **AND** backend status may describe `healthy`, `degraded`, `unavailable` or `not_configured` states where applicable

#### Scenario: AgentRun summary and detail stay structured
- **WHEN** a client reads AgentRun list or detail
- **THEN** AgentRun summary includes `run_id`, `event_id`, `trace_id`, `run_type`, `status`, `provider_policy`, `model_used`, timing fields and `error_summary`
- **AND** AgentRun detail may add `input_summary`, `output_summary`, related tool invocation refs and scheduler run ref
- **AND** AgentRun detail does not expose raw prompt or full reasoning chain

#### Scenario: ToolInvocation summary and detail stay structured
- **WHEN** a client reads ToolInvocation list or detail
- **THEN** ToolInvocation summary includes `invocation_id`, `agent_run_id`, `tool_id`, `plugin_id`, `risk_level`, `status`, retry and timing fields, and `error_summary`
- **AND** ToolInvocation detail may add `input_summary`, `output_summary` and approval reference
- **AND** ToolInvocation detail does not expose raw sensitive tool payloads

#### Scenario: SchedulerRun uses runtime-observation subset fields
- **WHEN** a client reads SchedulerRun list or detail from Runtime Inspect
- **THEN** SchedulerRun summary includes `run_id`, `binding_id`, `plugin_id`, `trigger_type`, `status`, timing fields and `error_summary`
- **AND** SchedulerRun detail may add event or captured-count summaries needed for runtime observation
- **AND** Runtime Inspect uses SchedulerRun summary/detail as an observation subset rather than inventing a separate incompatible object model

#### Scenario: RuntimeError summary and detail stay structured
- **WHEN** a client reads runtime errors
- **THEN** RuntimeError summary includes `error_id`, `component`, `severity`, `status`, `error_code`, `error_message_summary`, `trace_id` and creation time
- **AND** RuntimeError detail may add sanitized `details_summary` and related refs
- **AND** RuntimeError V1 remains read-only and does not require ack/ignore actions

### Requirement: Runtime Inspect V1 区分 empty、error 和 unavailable

Runtime Inspect V1 SHALL distinguish empty data, request failure and provider unavailability.

#### Scenario: empty list remains a successful read
- **WHEN** a list resource has no matching runtime objects
- **THEN** the API returns a successful envelope with an empty collection
- **AND** the client can distinguish this from provider failure

#### Scenario: provider unavailable stays controlled
- **WHEN** a runtime read model or downstream provider is temporarily unavailable
- **THEN** the API returns a controlled unavailable or degraded semantic
- **AND** it does not leak raw internal exceptions, stack traces, connection strings or local file paths

#### Scenario: request failures still use the standard error envelope
- **WHEN** a client sends invalid filters, requests an unknown id, or lacks permission
- **THEN** the API returns the standard error envelope
- **AND** detail reads can return `404`
- **AND** auth or capability failures can return `401` or `403`

### Requirement: Runtime Inspect V1 keeps REST as the state source of truth

Runtime Inspect V1 SHALL treat REST snapshots as the business-state source of truth and realtime channels only as refresh hints.

#### Scenario: initial page load uses REST
- **WHEN** a client opens the Runtime page or a runtime detail page
- **THEN** it reads the current state from REST resources
- **AND** the data model does not depend on an active websocket session to be complete

#### Scenario: realtime updates only hint refresh
- **WHEN** a realtime topic announces runtime changes
- **THEN** the client may refresh or patch the current view
- **AND** realtime transport does not replace REST detail queries or persisted read models

### Requirement: Runtime Inspect V1 enforces sanitized summaries instead of raw payload disclosure

Runtime Inspect V1 SHALL expose sanitized summaries and forbid raw sensitive runtime payloads in V1.

#### Scenario: summaries can be returned for debugging
- **WHEN** a client reads a runtime object detail
- **THEN** the API may return `input_summary`, `output_summary`, `error_summary` or other structured summaries
- **AND** these summaries remain sanitized and capability-safe

#### Scenario: raw sensitive payloads are not returned
- **WHEN** a runtime object contains prompt text, secret-bearing config, sensitive tool parameters or provider-native exception payloads
- **THEN** Runtime Inspect V1 does not return those raw values
- **AND** the API does not expose secrets, tokens, cookies, raw prompts, full reasoning traces, connection strings or provider stack traces

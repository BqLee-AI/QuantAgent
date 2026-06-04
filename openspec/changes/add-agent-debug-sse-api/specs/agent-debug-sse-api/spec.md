## ADDED Requirements

### Requirement: Debug Agent SSE endpoint is development-only
API SHALL expose Agent debug run SSE endpoints only in non-production environments and SHALL exclude them from production routing and production OpenAPI.

#### Scenario: Non-production debug stream is registered
- **WHEN** API app runs with `APP_ENV=development`, `test`, or `local`
- **THEN** `POST /api/v1/debug/agent-runs/fixtures/{fixture_id}/stream` is registered
- **AND** the endpoint is visible in non-production OpenAPI

#### Scenario: Production debug stream is not registered
- **WHEN** API app runs with `APP_ENV=production`
- **THEN** `POST /api/v1/debug/agent-runs/fixtures/{fixture_id}/stream` returns 404
- **AND** production `/openapi.json` does not contain this path

### Requirement: SSE stream starts a bounded debug fixture run
API SHALL allow non-production clients to start an allowlisted Agent debug fixture and receive a `text/event-stream` response backed by `AgentRuntime.run_stream`.

#### Scenario: NVDA primary fixture streams AgentRunEvent
- **WHEN** a non-production client starts fixture `semiconductor-nvda-earnings` with scenario `primary`
- **THEN** API returns `text/event-stream`
- **AND** the stream contains `run.started`, at least one intermediate event, and `run.completed` or `run.failed`
- **AND** intermediate events include todo, tool, subagent or artifact information from `AgentRunEvent`

#### Scenario: Unknown fixture is rejected before stream starts
- **WHEN** a client requests an unknown fixture id
- **THEN** API returns a non-streaming envelope error with an appropriate 4xx status
- **AND** no AgentRuntime run is started

### Requirement: SSE frame schema is stable and JSON-safe
API SHALL serialize every `AgentRunEvent` into stable SSE frames using the event type as the SSE event name and JSON data safe for frontend consumption.

#### Scenario: Event frame uses AgentRunEvent fields
- **WHEN** service serializes an `AgentRunEvent`
- **THEN** the SSE frame contains `event: <event.type>`
- **AND** the frame `data` JSON contains `event_id`, `agent_run_id`, `type`, `seq`, `created_at`, `payload`, `safe_summary`, and `trace_id`
- **AND** the frame does not dump raw Python object reprs

### Requirement: Router remains thin and service owns orchestration
API SHALL keep debug router as HTTP transport layer only, while `AgentDebugRunService` owns fixture lookup, runtime request creation and event streaming.

#### Scenario: Router delegates to service
- **WHEN** debug stream endpoint is invoked
- **THEN** router validates request DTO and calls a service method returning an async byte/string iterator
- **AND** router does not directly create DeepAgents, build business prompts, execute tools, or inspect fixture internals

#### Scenario: Service uses AgentRuntime boundary
- **WHEN** the service starts a fixture run
- **THEN** it uses `AgentRuntime.run_stream` or an injected runtime provider
- **AND** it does not call `create_deep_agent()` directly

### Requirement: Debug stream is safe on failure and disconnect
API SHALL handle runtime failure, service exception and client disconnect without exposing traceback, secret, full prompt, chain-of-thought or provider raw response.

#### Scenario: Runtime failure emits safe failed event
- **WHEN** AgentRuntime emits or raises a failure after stream start
- **THEN** SSE stream contains a `run.failed` frame or equivalent safe failure event
- **AND** payload contains only a sanitized error summary

#### Scenario: Client disconnect stops iteration
- **WHEN** client disconnects while stream is active
- **THEN** service stops iterating the runtime stream without writing additional state
- **AND** no traceback is returned to the client

## ADDED Requirements

### Requirement: SourceBinding V1 SHALL expose list and detail resources

The system SHALL expose `SourceBinding` as a REST resource with list and detail endpoints under `/api/v1/source-bindings`.

#### Scenario: List source bindings with stable summary fields

- **WHEN** a caller requests `GET /api/v1/source-bindings`
- **THEN** the API returns `ApiResponse` with a cursor-paginated collection of `SourceBindingSummary`
- **AND** each summary includes `id`, `source_plugin_id`, `owner_type`, `owner_id`, `status`, `blocked_reason`, `schedule_summary`, `last_run_ref`, `next_run_at`, `health_summary`, and `allowed_actions`
- **AND** the list endpoint supports explicit filters for `owner_type`, `owner_id`, `source_plugin_id`, and `status`
- **AND** the endpoint does not expose ORM-only fields, internal scheduler state objects, or secret-bearing config values

#### Scenario: Read source binding detail with masked config summary

- **WHEN** a caller requests `GET /api/v1/source-bindings/{binding_id}`
- **THEN** the API returns `ApiResponse` with `SourceBindingDetail`
- **AND** the detail includes summary fields plus `effective_config_summary`, `config_version`, `config_validation_status`, `rate_limit_policy_summary`, `retry_policy_summary`, `last_error_summary`, `audit_refs`, and `recent_run_refs`
- **AND** `effective_config_summary` only contains masked or non-sensitive fields, `secret_fields_masked`, `last_validated_at`, and config source references
- **AND** the endpoint does not expose secret plaintext, raw authentication headers, local filesystem paths, or runtime-injected scheduler objects

### Requirement: SourceBinding V1 SHALL expose binding-scoped run history without redefining the global SchedulerRun contract

The system SHALL expose binding-scoped `SchedulerRun` history through `/api/v1/source-bindings/{binding_id}/scheduler-runs` and SHALL reuse the existing Runtime Inspect `/api/v1/scheduler-runs*` contract as the only global public SchedulerRun truth source.

#### Scenario: List scheduler runs by binding without forking the global run model

- **WHEN** a caller requests `GET /api/v1/source-bindings/{binding_id}/scheduler-runs`
- **THEN** the API returns `ApiResponse` with a collection whose item field naming remains aligned with the existing Runtime Inspect `SchedulerRun` public model
- **AND** the endpoint supports explicit filters for `status`, `trigger_mode`, and time windows
- **AND** binding-scoped run history only returns runs associated with the requested `binding_id`
- **AND** the change does not publish a second incompatible global `/api/v1/scheduler-runs` list contract

#### Scenario: Global scheduler run detail remains owned by Runtime Inspect

- **WHEN** a caller needs global scheduler run list or detail under `/api/v1/scheduler-runs*`
- **THEN** the implementation reuses the Runtime Inspect contract truth source
- **AND** this change does not redefine detail field naming, pagination shape, or a second detail DTO for the same public resource

### Requirement: SourceBinding V1 SHALL expose `pause`, `resume`, and `run-now` as resource actions

The system SHALL expose binding control operations as resource-scoped actions under `/api/v1/source-bindings/{binding_id}/actions/*`.

#### Scenario: Pause and resume return accepted state envelopes

- **WHEN** a caller requests `POST /api/v1/source-bindings/{binding_id}/actions/pause` or `POST /api/v1/source-bindings/{binding_id}/actions/resume`
- **THEN** the API returns `ApiResponse` whose `data` contains the target `binding_id`, the accepted target state, `already_in_target_state`, `accepted_at`, and `audit_ref`
- **AND** repeating `pause` on an already paused binding or `resume` on an already active binding returns a successful idempotent envelope instead of an internal error
- **AND** the action outcome does not require the caller to infer state from free-form text

#### Scenario: Run-now is asynchronous command acceptance

- **WHEN** a caller requests `POST /api/v1/source-bindings/{binding_id}/actions/run-now`
- **THEN** the API returns `ApiResponse` whose `data` contains `binding_id`, `accepted_at`, `request_id`, and `requested_run_ref`
- **AND** the API does not wait for the scheduler execution to finish before responding
- **AND** the accepted response does not imply that fetch execution, RawEvent persistence, or downstream event publishing has already succeeded

### Requirement: SchedulerRun retry SHALL NOT be part of V1 public actions

The system SHALL exclude `SchedulerRun retry` from the V1 public action surface.

#### Scenario: V1 does not publish retry endpoint

- **WHEN** the V1 contract is generated for `SourceBinding` and `SchedulerRun`
- **THEN** it does not define `POST /api/v1/scheduler-runs/{run_id}/actions/retry`
- **AND** retry remains a follow-up capability that requires separate scheduler idempotency, audit, and replay design

### Requirement: Queries and actions SHALL enforce stable envelope, request id, permission, and audit semantics

The system SHALL apply unified response, error, request tracing, capability, and audit rules to all `SourceBinding` and `SchedulerRun` endpoints.

#### Scenario: Not found, permission denied, and invalid state transitions are structured

- **WHEN** a requested binding or run does not exist, the caller lacks capability, or an action violates binding state rules
- **THEN** the API returns the standard `ApiResponse` error envelope with `code`, `msg`, `error.code`, and `error.request_id`
- **AND** the response includes the same `X-Request-ID` value in headers and structured error payload
- **AND** the API uses stable error codes for not found, permission denied, and invalid state transitions instead of free-form stack traces

#### Scenario: All actions create auditable records

- **WHEN** a caller invokes `pause`, `resume`, or `run-now`
- **THEN** the system records an auditable action including `actor`, `action`, `target_type`, `target_id`, `result`, and `request_id`
- **AND** the accepted action response returns an `audit_ref` or equivalent stable reference
- **AND** the API does not allow front-end buttons or ad hoc clients to bypass capability or audit checks

### Requirement: REST SHALL remain the state source of truth for binding and run status

The system SHALL keep REST resources as the source of truth for `SourceBinding` and `SchedulerRun` state, while allowing future realtime channels to act only as refresh hints.

#### Scenario: Realtime notifications do not replace REST state reads

- **WHEN** binding status or run status changes are later emitted through a realtime channel
- **THEN** clients still use `GET /api/v1/source-bindings*` and the existing Runtime Inspect `GET /api/v1/scheduler-runs*` to recover authoritative state
- **AND** the realtime channel is not required to reconstruct binding detail, run detail, or action acceptance semantics

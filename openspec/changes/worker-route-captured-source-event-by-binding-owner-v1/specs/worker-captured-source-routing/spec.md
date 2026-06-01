## ADDED Requirements

### Requirement: Worker MUST 以 `binding_id` 为一级真源路由 `source.event.captured`
The system SHALL route `source.event.captured` in worker by `SourceBinding` ownership instead of routing by naked `source_plugin_id` or ad hoc owner guesses.

#### Scenario: Captured event contains stable binding identity
- **WHEN** scheduler or plugin scheduling publishes a `source.event.captured` event for worker consumption
- **THEN** the event MUST contain a stable `binding_id`
- **AND** worker routing MUST treat `binding_id` as the primary routing key
- **AND** worker MUST NOT choose target owner only from `plugin_id`

#### Scenario: Missing binding identity becomes controlled failure
- **WHEN** worker receives a `source.event.captured` event without `binding_id`
- **THEN** worker MUST return a controlled routing failure
- **AND** the failure MUST include a structured reason code for missing binding identity
- **AND** worker MUST NOT invoke any downstream industry entrypoint

### Requirement: Worker MUST resolve `SourceBinding` ownership before invoking industry entrypoint
The system SHALL load `SourceBinding` ownership and binding status before routing a captured event to any owner-specific processing entrypoint.

#### Scenario: Active industry binding routes to industry entrypoint
- **WHEN** worker receives a captured event with a valid `binding_id`
- **AND** the referenced `SourceBinding` exists and is `active`
- **AND** the binding owner is `owner_type == "industry"`
- **THEN** worker MUST resolve the industry owner from the binding record
- **AND** worker MUST invoke the controlled industry entrypoint for that owner

#### Scenario: Missing binding blocks downstream invocation
- **WHEN** worker receives a captured event whose `binding_id` does not exist
- **THEN** worker MUST return a controlled routing failure
- **AND** the failure MUST preserve `binding_id`, `message_id`, and owner lookup context for audit
- **AND** worker MUST NOT invoke any downstream industry entrypoint

#### Scenario: Non-active binding is not routed
- **WHEN** worker receives a captured event whose binding exists but is not `active`
- **THEN** worker MUST NOT route the event to downstream industry processing
- **AND** worker MUST produce a controlled `ignored` result with structured reason code `SOURCE_BINDING_NOT_ACTIVE`
- **AND** worker MUST treat the message as `ack_and_record_ignored` instead of a retryable failure

### Requirement: V1 successful routing MUST only support `industry` owner
The system SHALL support successful captured-event routing only for `owner_type == "industry"` in V1, while keeping other owner types behind controlled failure semantics.

#### Scenario: Unsupported owner type does not fall back to plugin routing
- **WHEN** worker resolves a binding whose `owner_type` is not `industry`
- **THEN** worker MUST return a controlled unsupported-owner failure
- **AND** worker MUST NOT fall back to routing by `plugin_id`
- **AND** worker MUST NOT guess a target owner from payload metadata

### Requirement: `industry_gateway` MUST remain a core port with structured results
The system SHALL keep `industry_gateway` as a core worker-routing port instead of directly importing or branching on concrete industry plugin implementations.

#### Scenario: V1 gateway can be fake or no-op but still returns structured result
- **WHEN** V1 implementation has not yet connected a real industry processing seam
- **THEN** `industry_gateway` MAY use a fake or no-op adapter
- **AND** the adapter MUST still return a structured result that includes status, reason code, and target reference fields
- **AND** worker routing MUST classify the final route result from that structured gateway response rather than from log strings

#### Scenario: Gateway does not directly import industry plugins
- **WHEN** worker routing invokes `industry_gateway`
- **THEN** the gateway MUST depend on a core port / protocol boundary
- **AND** the gateway MUST NOT directly import `plugins/industries/*` modules
- **AND** the gateway MUST NOT hardcode plugin registration with owner-specific `if/else` branches

### Requirement: Worker MUST expose stable route-result mapping for failure and duplicate semantics
The system SHALL publish a stable mapping from worker routing reason codes to route status, consumer disposition, retryability, and audit requirements.

#### Scenario: Binding identity missing maps to non-retryable failure
- **WHEN** worker returns reason code `CAPTURED_EVENT_BINDING_ID_MISSING`
- **THEN** route status MUST be `failed`
- **AND** consumer disposition MUST be `ack_and_record_failure`
- **AND** retryable MUST be `false`
- **AND** audit MUST be required

#### Scenario: Missing binding maps to non-retryable failure
- **WHEN** worker returns reason code `SOURCE_BINDING_NOT_FOUND`
- **THEN** route status MUST be `failed`
- **AND** consumer disposition MUST be `ack_and_record_failure`
- **AND** retryable MUST be `false`
- **AND** audit MUST be required

#### Scenario: Duplicate message maps to duplicate disposition
- **WHEN** worker returns reason code `CAPTURED_EVENT_DUPLICATE`
- **THEN** route status MUST be `duplicate`
- **AND** consumer disposition MUST be `ack_and_record_duplicate`
- **AND** retryable MUST be `false`
- **AND** audit MUST be required

### Requirement: Worker captured-event routing MUST be idempotent and auditable
The system SHALL express duplicate handling and routing outcomes as structured worker-side results instead of relying on implicit consumer behavior or raw log strings.

#### Scenario: Duplicate message does not trigger downstream side effects twice
- **WHEN** worker receives the same captured-event message more than once
- **THEN** worker MUST classify the later delivery as a duplicate or equivalent idempotent outcome
- **AND** worker MUST NOT invoke the downstream industry entrypoint twice for the same message

#### Scenario: Downstream entrypoint failure preserves audit context
- **WHEN** worker resolves a valid industry owner but the downstream entrypoint fails
- **THEN** worker MUST return a structured routing failure
- **AND** the result MUST preserve `binding_id`, `owner_type`, `owner_id`, and message identity for audit
- **AND** worker MUST NOT silently swallow the failure

#### Scenario: Downstream gateway failure remains retryable and auditable
- **WHEN** worker returns reason code `INDUSTRY_ENTRYPOINT_FAILED`
- **THEN** route status MUST be `failed`
- **AND** consumer disposition MUST be `nack_or_schedule_retry`
- **AND** retryable MUST be `true`
- **AND** audit MUST be required

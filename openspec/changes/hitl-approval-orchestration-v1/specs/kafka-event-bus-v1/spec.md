## MODIFIED Requirements

### Requirement: Event Bus V1 restricts topic names through topic policy

Event Bus V1 SHALL validate event topics against a stable topic policy.

#### Scenario: default topic set is accepted
- **WHEN** a publisher validates a V1 topic
- **THEN** `source.event.captured` is accepted
- **AND** `event.routed` is accepted
- **AND** `industry.analysis.requested` is accepted
- **AND** `industry.analysis.completed` is accepted
- **AND** `analysis.scored` is accepted
- **AND** `decision.created` is accepted
- **AND** `action.requested` is accepted
- **AND** `approval.requested` is accepted
- **AND** `approval.input_received` is accepted
- **AND** `approval.completed` is accepted
- **AND** `notification.requested` is accepted
- **AND** `notification.completed` is accepted
- **AND** `broker.dry_run_requested` is accepted
- **AND** `broker.dry_run_completed` is accepted
- **AND** `runtime.failed` is accepted

#### Scenario: unknown topic is rejected
- **WHEN** a publisher attempts to publish an envelope with an unregistered topic
- **THEN** Event Bus V1 rejects the envelope before sending it to Kafka or the memory fake
- **AND** the rejection is represented as a structured event bus error

### Requirement: Event Bus V1 protects sensitive data in errors and logs

Event Bus V1 SHALL prevent secrets and sensitive local context from appearing in event bus errors, headers, payload diagnostics, and logs.

#### Scenario: event bus error summary is sanitized
- **WHEN** publish, decode, subscribe, or handler dispatch fails
- **THEN** the structured error summary does not expose secret values
- **AND** it does not expose tokens, cookies, full local private paths, full stack traces, full prompts, or private strategy text

#### Scenario: envelope diagnostics are safe for review
- **WHEN** tests or logs record envelope diagnostics
- **THEN** they may include topic, envelope id, producer, schema version, retry count, and safe error code
- **AND** they do not include raw sensitive payload fields or secret-bearing headers

#### Scenario: HITL approval topics preserve sanitized diagnostics
- **WHEN** `action.requested` or `approval.input_received` publish, decode, subscribe, or handler dispatch fails
- **THEN** diagnostics may include topic, envelope id, producer, schema version, retry count, approval id, action request id, and safe error code
- **AND** diagnostics do not include raw user text, complete prompt text, private strategy text, broker credentials, API keys, cookies, tokens, or secret-bearing headers

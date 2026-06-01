## ADDED Requirements

### Requirement: Successful notification receive items become platform facts

QuantAgent SHALL turn a successful `notification.receive` item into a platform-owned `NotificationReceiveFact` before any later approval-domain processing.

#### Scenario: response-only success does not create a fact
- **WHEN** a notification plugin returns `accepted=true`
- **AND** the result contains a protocol `response`
- **AND** the result does not contain `item`
- **THEN** the platform returns the protocol response
- **AND** the platform does not create a `NotificationReceiveFact`
- **AND** the platform does not trigger approval handoff

#### Scenario: success with item creates a fact
- **WHEN** a notification plugin returns `accepted=true`
- **AND** the result contains a valid `item`
- **THEN** the platform creates a `NotificationReceiveFact`
- **AND** that fact contains `plugin_id`
- **AND** that fact contains `transport`
- **AND** that fact contains `request_id`
- **AND** that fact contains `correlation_id`
- **AND** that fact contains `interaction_id`
- **AND** that fact contains `source_id`
- **AND** that fact contains `text`

### Requirement: Notification ingress audit remains append-only and platform-owned

QuantAgent SHALL append platform-owned audit entries when a notification receive fact is recorded or handed off.

#### Scenario: fact creation appends an audit entry
- **WHEN** the platform records a `NotificationReceiveFact`
- **THEN** it appends a `notification.receive.recorded` audit entry
- **AND** the audit entry contains `plugin_id`
- **AND** the audit entry contains `request_id`
- **AND** the audit entry contains `correlation_id`
- **AND** the audit entry contains a reference to the created fact

#### Scenario: approval handoff appends an audit entry
- **WHEN** the platform hands a receive fact to the approval handoff port
- **THEN** it appends a `notification.receive.approval_handoff` audit entry
- **AND** the audit entry contains the fact reference
- **AND** the audit entry contains the handoff status

#### Scenario: approval handoff failure keeps the fact and appends failed audit
- **WHEN** the platform has already recorded a `NotificationReceiveFact`
- **AND** the approval handoff port raises an error
- **THEN** the platform keeps the recorded fact
- **AND** it appends a `notification.receive.approval_handoff_failed` audit entry
- **AND** the returned handoff result indicates failure

### Requirement: Approval handoff is an explicit seam, not approval orchestration itself

QuantAgent SHALL expose notification-to-approval transfer as a dedicated handoff port rather than embedding approval orchestration into notification ingress.

#### Scenario: default handoff can safely no-op
- **WHEN** notification ingress is configured with the default handoff implementation
- **THEN** a successful receive fact can still be recorded
- **AND** the handoff result explicitly indicates that no approval workflow is configured yet
- **AND** the system does not claim approval is completed

#### Scenario: custom handoff receives normalized platform data
- **WHEN** notification ingress is configured with a custom handoff implementation
- **THEN** the handoff implementation receives a `NotificationApprovalHandoffRequest`
- **AND** that request contains the receive fact identity and correlation fields
- **AND** that request does not expose FastAPI objects
- **AND** that request does not expose DB sessions
- **AND** that request does not expose plugin implementation objects

### Requirement: This change does not implement approval-domain topics or state machine

Notification receive handoff V1 SHALL avoid taking over the approval orchestration responsibilities that belong to the HITL approval change.

#### Scenario: notification ingress does not publish approval topics
- **WHEN** notification ingress records a fact and performs handoff
- **THEN** it does not itself publish `approval.requested`
- **AND** it does not itself publish `approval.completed`
- **AND** it does not itself create approval-domain state transitions

#### Scenario: notification ingress does not evaluate approval policy
- **WHEN** notification ingress performs handoff
- **THEN** it does not evaluate policy gate logic
- **AND** it does not decide approve or reject outcomes
- **AND** it only transfers normalized receive facts to a later approval-domain seam

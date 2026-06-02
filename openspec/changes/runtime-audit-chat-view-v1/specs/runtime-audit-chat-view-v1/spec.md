## ADDED Requirements

### Requirement: Runtime page MUST prioritize audit chat flow over multi-panel dashboard layout

`/runtime` SHALL present a Chat App style audit flow as its primary V1 experience, so users can review one event or Agent run as a sequence of structured audit messages.

#### Scenario: Runtime first screen uses audit conversation
- **WHEN** a user opens `/runtime`
- **THEN** the primary content MUST be an audit conversation or timeline-style message flow
- **AND** it MUST NOT default to four separate list panels for AgentRun, ToolInvocation, SchedulerRun and RuntimeError
- **AND** health information MAY appear only as a compact status strip or folded diagnostic detail

#### Scenario: Runtime preserves investigation filters
- **WHEN** a user investigates runtime behavior
- **THEN** the page MUST support lightweight filters such as `event_id`, `trace_id`, decision, status, industry and time range
- **AND** filters MUST update audit flow query state rather than driving independent table panels as the primary page structure

### Requirement: Runtime audit messages MUST be structured, traceable and safe to inspect

Runtime audit chat SHALL use structured audit message objects that preserve trace context and expose only sanitized summaries.

#### Scenario: Message preserves trace context
- **WHEN** an audit message is rendered
- **THEN** it MUST preserve available event, trace, request, correlation and source message context
- **AND** it MUST expose enough identity for a user to connect the message back to the source event or routed event
- **AND** it MUST NOT require reading raw logs to understand the basic transition represented by the message

#### Scenario: Message details stay sanitized
- **WHEN** a user expands a message detail
- **THEN** the detail MUST show only structured summary fields or sanitized safe details
- **AND** it MUST NOT show raw prompt, full chain-of-thought, provider raw response, secret values, ORM objects, plugin instances, connection strings or raw sensitive tool payloads
- **AND** payload-like details MUST be represented as safe summaries or field references

### Requirement: Router Agent MUST be the first audit showcase

Runtime audit chat V1 SHALL use Router Agent / AI intake routing as the first showcase flow.

#### Scenario: Route decision is auditable
- **WHEN** an intake item is routed
- **THEN** the audit flow MUST show `industry.analysis.requested` as the upstream request
- **AND** it MUST show the single-call intake decision summary
- **AND** it MUST show `event.routed` as the routing handoff
- **AND** it MUST preserve target industries, target topics, priority, confidence or equivalent routing summary

#### Scenario: Discard decision is auditable
- **WHEN** an intake item is discarded
- **THEN** the audit flow MUST show the discard decision as a terminal outcome for deep analysis
- **AND** it MUST include a structured discard reason such as spam, irrelevant, duplicate hint, low information, unsupported language or malformed input
- **AND** it MUST keep enough audit-safe reason summary for a user to understand why tokens were saved

#### Scenario: Review decision is auditable
- **WHEN** an intake item requires review
- **THEN** the audit flow MUST distinguish review from route and discard
- **AND** it MUST show uncertainty, low-confidence or human-review reason
- **AND** it MUST NOT represent review as successful deep-analysis routing

### Requirement: Runtime audit chat MUST represent degraded and failed intake states explicitly

Runtime audit chat SHALL display degraded input and failure states as first-class audit messages or badges.

#### Scenario: Degraded RSS-summary input is visible
- **WHEN** AI intake consumed RSS summary because article enrichment failed
- **THEN** the audit flow MUST show a degraded or RSS-summary-only marker
- **AND** it MUST NOT represent the item as if full article text had been obtained

#### Scenario: Schema validation failure is visible
- **WHEN** model output fails `EventIntakeDecisionV1` validation or equivalent schema validation
- **THEN** the audit flow MUST show a validation failure message
- **AND** it MUST NOT silently route the item as if validation succeeded
- **AND** safe error summary MAY be shown without exposing raw provider output

#### Scenario: Provider or runtime unavailable is visible
- **WHEN** provider, model invocation, Runtime Inspect or audit read source is unavailable
- **THEN** the page MUST keep already available audit messages visible
- **AND** unavailable stages MUST be marked as partial unavailable, warning or error states
- **AND** the page MUST NOT collapse the whole audit flow into an unrelated generic empty state

### Requirement: Runtime audit chat implementation MUST follow Web feature boundaries

The web implementation SHALL keep route, API, query, hook, component, type and utility responsibilities separate.

#### Scenario: Route remains a thin entry
- **WHEN** `/runtime` is implemented or refactored
- **THEN** the route file MUST only handle TanStack route setup, search params and page mounting
- **AND** it MUST NOT implement API calls, query keys, audit message formatting, large JSX bodies or selection state

#### Scenario: Feature files have single responsibilities
- **WHEN** Runtime audit chat files are added under `features/runtime`
- **THEN** API contracts MUST live under `api/`
- **AND** TanStack Query hooks and query keys MUST live under `queries/`
- **AND** page-level composition and local UI state MUST live under `hooks/`
- **AND** conversation, message, detail and state views MUST live under `components/`
- **AND** local display types MUST live under `types/`
- **AND** formatting, sanitization and fixture conversion MUST live under `utils/`
- **AND** the feature README MUST document responsibilities, entrypoints and raw payload restrictions

### Requirement: PR #257 MUST be handled as an unmerged input, not as accepted mainline behavior

The system SHALL treat PR #257 as an unmerged implementation input whose page layer must be re-evaluated against this audit-chat spec.

#### Scenario: Reusable pieces are separated from page layout
- **WHEN** implementation work proceeds after this change
- **THEN** Runtime Inspect contracts, query layering, REST snapshot behavior, partial unavailable handling and sanitized summary fields from PR #257 MAY be reused
- **AND** the multi-panel dashboard first screen MUST NOT be accepted as the final V1 `/runtime` experience without explicit maintainer approval

#### Scenario: Mainline does not keep two competing runtime first screens
- **WHEN** a PR implements Runtime audit chat
- **THEN** it MUST explain whether PR #257 was modified, partially reused, superseded or closed
- **AND** mainline MUST NOT keep both a multi-panel Runtime Dashboard first screen and an audit chat first screen for the same `/runtime` route

### Requirement: Runtime audit chat SHALL allow controlled fixture showcase before production audit read model is available

Runtime audit chat V1 SHALL allow controlled fixtures to validate UI behavior when production audit read APIs are not ready.

#### Scenario: Fixture mode is clearly marked
- **WHEN** controlled fixtures are used for Router Agent audit showcase
- **THEN** the implementation MUST make fixture ownership clear in code and documentation
- **AND** it MUST NOT claim that production audit read model is complete
- **AND** fixture data MUST NOT include real secrets, raw prompts, provider raw responses or production payloads

#### Scenario: Fixture coverage proves the target behavior
- **WHEN** fixture-based validation is run
- **THEN** fixtures MUST cover route, discard, review, degraded RSS-summary input and schema validation failure
- **AND** tests or manual harness MUST prove these cases render as distinct audit states

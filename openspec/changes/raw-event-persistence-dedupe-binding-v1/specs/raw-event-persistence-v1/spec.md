## ADDED Requirements

### Requirement: RawEvent V1 SHALL persist canonical source items separately from ownership captures

The system SHALL persist canonical RawEvent content and binding/run ownership history as separate persistence records instead of collapsing both concerns into a single duplicate counter row.

#### Scenario: First capture creates both canonical row and ownership row
- **WHEN** the platform persists a new source item whose canonical identity does not yet exist for the same `source_plugin_id`
- **THEN** it MUST create one canonical `RawEvent`
- **AND** it MUST create one `RawEventCapture` linked to that canonical row
- **AND** the canonical row MUST include structured source fields such as `external_id`, `canonical_url`, `title`, `content`, `author`, `published_at`, and `captured_at` where available
- **AND** the ownership row MUST include `binding_id` and `run_id` when the capture originates from scheduler-owned source ingestion

#### Scenario: Duplicate capture reuses canonical row but keeps ownership history
- **WHEN** a later binding or scheduler run captures a source item whose canonical identity already exists for the same `source_plugin_id`
- **THEN** the platform MUST reuse the existing canonical `RawEvent`
- **AND** it MUST append a new ownership `RawEventCapture`
- **AND** it MUST NOT create a second canonical `RawEvent` for that same canonical identity
- **AND** any duplicate counter on the canonical row MUST NOT replace the append-only ownership history

### Requirement: RawEvent canonical dedupe SHALL be scoped within `source_plugin_id`

The system SHALL compute canonical RawEvent dedupe within a single `source_plugin_id`, while keeping `binding_id` and `run_id` as ownership references rather than canonical identity inputs.

#### Scenario: Dedupe does not split canonical identity by binding
- **WHEN** two different bindings of the same source plugin capture the same canonical source item
- **THEN** the platform MUST treat them as the same canonical `RawEvent`
- **AND** it MUST represent the different bindings through separate ownership captures

#### Scenario: Dedupe does not merge across different source plugins
- **WHEN** two different source plugins capture source items with the same URL or similar content
- **THEN** the platform MUST NOT assume they share the same canonical `RawEvent`
- **AND** canonical dedupe MUST still remain scoped by `source_plugin_id`

### Requirement: RawEvent dedupe priority SHALL follow platform-controlled canonical identity rules

The system SHALL compute canonical RawEvent identity using platform-controlled priority rules instead of trusting plugins to provide a final dedupe key.

#### Scenario: `external_id` wins when present
- **WHEN** a source item includes a stable `external_id`
- **THEN** the platform MUST compute canonical identity from `source_plugin_id + external_id`
- **AND** lower-priority fallback material MUST NOT replace that identity

#### Scenario: URL and content hash form the fallback identity
- **WHEN** a source item does not include `external_id` but includes canonicalizable URL and stable content material
- **THEN** the platform MUST compute canonical identity from `source_plugin_id + canonical_url + content_hash`

#### Scenario: Provider hint is only a controlled third fallback
- **WHEN** a source item lacks both `external_id` and usable `canonical_url + content_hash`
- **THEN** the platform MAY use a provider-supplied dedupe hint as the third fallback
- **AND** that hint MUST be JSON-safe, auditable, and free of secrets
- **AND** the plugin MUST NOT bypass platform dedupe priority by directly supplying the final canonical key

### Requirement: RawEvent ownership writes SHALL remain idempotent and safe under concurrent duplicate upserts

The system SHALL prevent concurrent duplicate ingestion from producing multiple canonical rows for the same canonical identity or multiple equivalent ownership rows for the same run.

#### Scenario: Canonical uniqueness holds under concurrent upsert
- **WHEN** two concurrent writers persist the same canonical source identity for the same `source_plugin_id`
- **THEN** database uniqueness MUST guarantee that only one canonical `RawEvent` is created
- **AND** the losing writer MUST resolve by reading the existing canonical row instead of creating another one

#### Scenario: Same run retry does not duplicate ownership row
- **WHEN** the same `run_id` retries persistence for the same canonical source identity because of a transient database or worker retry
- **THEN** the platform MUST return the existing ownership semantics for that run
- **AND** it MUST NOT append a second equivalent `RawEventCapture` for that same run and canonical identity

#### Scenario: Different runs still keep separate ownership history
- **WHEN** a later scheduler retry or later scheduled execution uses a different `run_id` and captures the same canonical source identity
- **THEN** the platform MUST keep a separate ownership `RawEventCapture`
- **AND** that capture MUST still point at the same canonical `RawEvent`

### Requirement: RawEvent payload SHALL remain structured, redacted, and bounded

The system SHALL keep RawEvent payload storage within a controlled, auditable boundary instead of treating `raw_payload` as an unbounded black-box blob.

#### Scenario: High-value source fields are structured outside `raw_payload`
- **WHEN** the platform persists a RawEvent
- **THEN** high-value query and replay fields such as `external_id`, `canonical_url`, `title`, `content`, `author`, `published_at`, and canonical dedupe material MUST NOT exist only inside `raw_payload`

#### Scenario: Sensitive or host-only data is excluded from `raw_payload`
- **WHEN** a source item carries secret-bearing or host-internal context
- **THEN** `raw_payload` MUST NOT persist secrets, tokens, cookies, auth headers, signed URL credentials, ORM objects, database sessions, or service references
- **AND** it MUST NOT persist full HTML snapshots, binary attachments, or other future large-object concerns

#### Scenario: Oversized payload is trimmed or rejected within the V1 cap
- **WHEN** serialized `raw_payload` would exceed 128 KiB
- **THEN** the platform MUST first reduce it to an allowlisted subset
- **AND** if the payload still exceeds the V1 cap, the platform MUST reject the write with a structured error instead of silently persisting an oversized blob
- **AND** any accepted truncation MUST leave an auditable truncation marker

### Requirement: RawEvent persistence SHALL reuse scheduler binding/run identity without exposing ORM models

The system SHALL reuse `binding_id` and `run_id` from scheduler persistence as stable ownership references while keeping ORM models internal to core persistence.

#### Scenario: Scheduler-owned capture keeps binding and run references
- **WHEN** issue #217 or a future scheduler-owned ingestion flow persists a source item
- **THEN** the resulting ownership record MUST reuse the same `binding_id` and `run_id` naming defined by scheduler persistence
- **AND** scheduler-owned ingestion MUST NOT invent a second ownership identity vocabulary

#### Scenario: Adjacent changes do not expose ORM objects as external DTOs
- **WHEN** future API or Event normalization changes consume RawEvent persistence results
- **THEN** they MUST reference canonical RawEvent and ownership identifiers through service boundaries
- **AND** they MUST NOT expose `RawEvent` or `RawEventCapture` ORM models directly as external DTOs

### Requirement: RawEvent V1 acceptance SHALL be validated against PostgreSQL behavior

The system SHALL treat PostgreSQL as the target database truth source for RawEvent persistence acceptance, while allowing SQLite only as a supplementary harness.

#### Scenario: PostgreSQL validates canonical upsert and ownership idempotency
- **WHEN** the implementation PR claims RawEvent V1 persistence is complete
- **THEN** it MUST verify canonical uniqueness, concurrent duplicate upsert resolution, and same-run ownership idempotency on PostgreSQL
- **AND** SQLite-only validation MUST NOT be presented as sufficient acceptance evidence

#### Scenario: PostgreSQL validation result is explicit in PR evidence
- **WHEN** the implementation PR is prepared for review
- **THEN** the PR description MUST explicitly state whether PostgreSQL migration and duplicate-ingestion validation were run
- **AND** any missing PostgreSQL validation MUST be called out as an unverified risk

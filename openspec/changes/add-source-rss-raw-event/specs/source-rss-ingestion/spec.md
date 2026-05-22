## ADDED Requirements

### Requirement: Pull Source Plugin Contract

The system SHALL define a minimum pull Source Plugin contract that can be consumed by core runtime services without depending on a concrete plugin implementation.

#### Scenario: Pull source exposes lifecycle and fetch operations

- **WHEN** a pull source plugin is used by the runtime
- **THEN** it SHALL expose `load`, `start`, `stop`, `reload`, `health_check`, and `fetch` operations

#### Scenario: Source plugin does not self-schedule

- **WHEN** a pull source plugin fetches external data
- **THEN** it MUST NOT start its own polling loop, background thread, or long-running scheduler

### Requirement: RawEvent Persistence

The system SHALL persist source output as RawEvent records before later standardization into Event records.

#### Scenario: New raw event is stored

- **WHEN** a Source Plugin returns a new RawEvent draft
- **THEN** the system SHALL store source plugin id, source type, title, URL fields, published time, captured time, raw payload, metadata, dedupe key, and dedupe reason

#### Scenario: RawEvent DTO is separate from ORM

- **WHEN** source code passes raw event data across runtime boundaries
- **THEN** it MUST use DTOs rather than returning ORM models as Source Plugin DTOs

### Requirement: RawEvent Deduplication

The system SHALL deduplicate RawEvent records before inserting duplicates into storage.

#### Scenario: External id dedupe

- **WHEN** a RawEvent draft has an external id
- **THEN** the system SHALL deduplicate by `source_plugin_id + external_id`

#### Scenario: URL and content dedupe fallback

- **WHEN** a RawEvent draft does not have an external id but has URL and content or title data
- **THEN** the system SHALL deduplicate using source plugin id, canonical URL, and content hash

#### Scenario: Duplicate event is skipped

- **WHEN** a duplicate RawEvent draft is processed
- **THEN** the system SHALL skip inserting a second RawEvent record and report the duplicate in the fetch result

### Requirement: SourceBinding Fetch Run Recording

The system SHALL trigger pull source fetches through a SourceBinding context and record each fetch run.

#### Scenario: Successful fetch run is recorded

- **WHEN** a SourceBinding fetch completes successfully
- **THEN** the system SHALL record source binding id, source plugin id, status, fetched count, stored count, duplicate count, duration, start time, and finish time

#### Scenario: Failed fetch run is recorded

- **WHEN** a SourceBinding fetch fails
- **THEN** the system SHALL record failed status and a structured error summary without exposing secrets

### Requirement: RSS Source Plugin

The system SHALL provide an official RSS Source Plugin registered through `plugin.yaml`.

#### Scenario: RSS plugin manifest is discoverable

- **WHEN** the plugin discovery scans official source plugins
- **THEN** it SHALL discover `quantagent.official.source.rss` as a source plugin with pull execution mode and `source.fetch` capability

#### Scenario: RSS feed item becomes RawEvent draft

- **WHEN** the RSS Source Plugin parses an RSS or Atom feed item
- **THEN** it SHALL return a RawEvent draft with source plugin id, source type, title, URL, external id when available, published time when available, raw payload, and metadata

#### Scenario: RSS plugin avoids unrelated behavior

- **WHEN** the RSS Source Plugin processes feed data
- **THEN** it MUST NOT perform industry routing, analysis, notification, execution, Playwright crawling, proxy handling, or browser automation

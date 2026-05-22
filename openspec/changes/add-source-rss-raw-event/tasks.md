## 1. Source Runtime Contract

- [x] 1.1 Define RawEvent DTOs for source output and stored event summaries.
- [x] 1.2 Define pull Source Plugin protocol with lifecycle and fetch operations.
- [x] 1.3 Define SourceBindingConfig as the minimum runtime binding context.

## 2. Persistence

- [x] 2.1 Add ORM models for RawEvent, SourceBinding, and SourceFetchRun.
- [x] 2.2 Add Alembic migration for `raw_events`, `source_bindings`, and `source_fetch_runs`.
- [x] 2.3 Implement RawEvent repository with dedupe-aware insert behavior.
- [x] 2.4 Import source models into SQLAlchemy metadata for tests and migrations.

## 3. Fetch Execution

- [x] 3.1 Implement SourceFetchService to trigger one pull fetch through SourceBindingConfig.
- [x] 3.2 Record successful fetch count, stored count, duplicate count, duration, and timestamps.
- [x] 3.3 Record failed fetch status and structured error summary.
- [x] 3.4 Ensure SourceFetchService owns stop handling instead of relying on plugin self-scheduling.

## 4. RSS Source Plugin

- [x] 4.1 Add official RSS Source Plugin manifest with pull execution mode and `source.fetch` capability.
- [x] 4.2 Add RSS Source config JSON Schema for feed list, timeout, user agent, and max item limit.
- [x] 4.3 Implement minimal RSS / Atom parsing to RawEventDraft using standard library.
- [x] 4.4 Add plugin README documenting source-only boundaries and config ownership.

## 5. Verification

- [x] 5.1 Add unit tests for RawEvent dedupe insert behavior.
- [x] 5.2 Add unit tests for SourceFetchService success and failure run recording.
- [x] 5.3 Add unit tests for RSS Source manifest discovery.
- [x] 5.4 Add unit tests for RSS feed item parsing to RawEventDraft.
- [x] 5.5 Run core unit tests.
- [x] 5.6 Run Alembic upgrade validation with temporary SQLite URL.

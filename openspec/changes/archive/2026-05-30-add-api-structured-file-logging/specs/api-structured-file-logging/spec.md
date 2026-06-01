## ADDED Requirements

### Requirement: API Logging Bootstrap

`apps/api` SHALL provide an API-private structured file logging bootstrap that is explicit, idempotent, and safe for tests.

#### Scenario: App creation configures logging once

- **WHEN** `create_app()` builds a FastAPI app with API settings
- **THEN** the API logging bootstrap is configured through an explicit idempotent entrypoint
- **AND** repeated app creation in tests does not duplicate handlers or duplicate log records

#### Scenario: App shutdown flushes logging resources

- **WHEN** the FastAPI lifespan shuts down after logging was configured
- **THEN** the API stops the logging queue listener through an idempotent shutdown path
- **AND** queued records are flushed to their stream files before file handlers are closed as far as possible
- **AND** repeated app creation and shutdown in tests does not leave background logging threads, duplicate handlers, or open file descriptors

#### Scenario: Logging stays inside API boundary

- **WHEN** the first implementation of this capability is added
- **THEN** the logging infrastructure lives under `apps/api/src/quantagent/api/observability/`
- **AND** it does not create `packages/core/observability`
- **AND** FastAPI route functions do not assemble JSON log lines, file paths, rotation state, or redaction rules

### Requirement: Request Context And Trace Correlation

API requests SHALL bind a request context that keeps response headers, error envelopes, and log records correlated.

#### Scenario: Request id is consistent across response and logs

- **WHEN** a client sends a request with a valid `X-Request-ID`
- **THEN** the API preserves that request id in the response header
- **AND** every log record emitted inside that request context includes the same `request_id`
- **AND** any error envelope for that request includes the same `error.request_id`
- **AND** `get_request_id(request)` remains the public accessor and returns the same request id during the migration from `request.state` to contextvars

#### Scenario: Invalid request id is replaced consistently

- **WHEN** a client sends a missing or invalid `X-Request-ID`
- **THEN** the API generates a replacement request id
- **AND** the generated value is used consistently in the response header, error envelope, and log records

#### Scenario: Trace id is resolved without OpenTelemetry

- **WHEN** a request contains a valid W3C `traceparent`
- **THEN** the API uses the trace id from `traceparent`
- **AND** the response header, error envelope, and log records include that `trace_id`

#### Scenario: Trace id falls back to X-Trace-ID or generated value

- **WHEN** a request does not contain a usable `traceparent`
- **THEN** the API uses a valid `X-Trace-ID` when present
- **AND** otherwise generates a local trace id
- **AND** it does not require OpenTelemetry, an APM SDK, or an external collector

### Requirement: Structured Log Records

API logs SHALL be JSON Lines records with stable fields and stream-specific event names.

#### Scenario: Access log contains required request fields

- **WHEN** an HTTP request completes
- **THEN** exactly one API access log record is emitted for that request when queue degradation is not active
- **AND** if queue degradation is active, the API still attempts to emit the access record before any configured drop, sampling, or aggregation rule is applied
- **AND** the record includes `event`, `stream`, `service`, `env`, `instance_id`, `pid`, `request_id`, `trace_id`, `method`, `path`, `status_code`, and `duration_ms`
- **AND** the record is valid single-line JSON

#### Scenario: Error log captures safe exception metadata

- **WHEN** an unhandled exception is converted to the standard error envelope
- **THEN** an error stream record is emitted with `request_id`, `trace_id`, `exception_type`, and safe error metadata
- **AND** the client receives a generic 500 envelope
- **AND** neither the log record nor the response exposes traceback text, secrets, cookie values, or database connection strings

#### Scenario: Handled service failures emit error records

- **WHEN** DB readiness, DB session creation, or another handled service dependency failure is converted to a typed error response
- **THEN** an error stream record is emitted with `event`, `request_id`, `trace_id`, `component`, `failure_type`, and safe error metadata
- **AND** the error record identifies the handled failure path without exposing database connection strings, SQL parameters, secrets, or traceback text

#### Scenario: Security and audit events are emitted to required streams

- **WHEN** auth failure, CSRF failure, unauthorized access, or forbidden access occurs
- **THEN** a security event record is emitted to the `security` stream
- **AND** the record includes `event`, `request_id`, `trace_id`, `actor_type` when known, and safe failure metadata
- **WHEN** a protected write or high-risk action context occurs
- **THEN** an audit event record is emitted to the `audit` stream
- **AND** the `audit` stream is not treated as the future append-only database `audit_logs` business audit source

### Requirement: File Stream Layout And Rotation

API file logs SHALL be grouped by stream, date, process, and time slice to support high request volume.

#### Scenario: Logs are written to stream date directories

- **WHEN** the API writes file logs
- **THEN** each record is routed to `LOG_DIR/{stream}/YYYY/MM/DD/`
- **AND** the default `LOG_DIR` resolves to `RUNTIME_DIR/logs/api`
- **AND** file management, rotation, and cleanup logic use the resolved `LOG_DIR` instead of hardcoding the repository root `runtime/` string
- **AND** the logging module resolves `LOG_DIR` to an absolute path at initialization so that a relative `RUNTIME_DIR` is anchored to the process cwd at startup rather than drifting with subsequent cwd changes
- **AND** supported streams include at least `access`, `app`, `error`, `security`, and `audit`
- **AND** route name, actor, source, status code, and event type are stored as JSON fields rather than as separate physical file names

#### Scenario: Active file name includes process identity

- **WHEN** a process opens an active log file
- **THEN** the file name follows `{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDDTHH}[.part-NNN].jsonl`
- **AND** the `T` in `YYYYMMDDTHH` is a literal separator between the date and hour fields
- **AND** a valid example file name is `api.production.pod-api-7d9c9.pid-123.access.20260528T14.jsonl`
- **AND** separate API processes write separate active files
- **AND** the implementation does not rely on cross-process locks for normal active file writes
- **AND** directory date placeholders use `YYYY/MM/DD` while file hour-slice placeholders use `YYYYMMDDTHH`

#### Scenario: Rotation uses hour and size boundaries

- **WHEN** the current hour changes
- **THEN** the writer switches to a new hour-sliced file
- **AND** when the current file exceeds the configured maximum size
- **THEN** the writer switches to the next `part-NNN` file for the same hour

### Requirement: Queue Based Write Path

API logging SHALL use a queue based write path in stage 1 so ordinary requests do not directly perform normal file IO.

#### Scenario: Request path enqueues structured records

- **WHEN** request handling emits access, app, error, security, or audit records
- **THEN** the request path creates structured records and enqueues them
- **AND** a background listener writes queued records to the corresponding stream files
- **AND** ordinary request handling does not synchronously write normal log records to stream files

#### Scenario: Queue full degradation protects critical logs

- **WHEN** the logging queue is full
- **THEN** access logs may be dropped, sampled, or aggregated according to configuration
- **AND** error, security, and audit events are preserved as far as possible
- **AND** if critical records still cannot be queued, the API uses a bounded fallback path or emits at least one redacted local stderr warning
- **AND** fallback handling does not recursively emit new structured log records or block indefinitely
- **AND** queue full or dropped access events are observable through an internal counter or log event

#### Scenario: Queue shutdown does not lose queued records silently

- **WHEN** the application is shutting down
- **THEN** the logging queue listener is asked to drain queued records before stopping
- **AND** shutdown uses a bounded wait so API shutdown cannot block indefinitely
- **AND** if queued records cannot be fully drained, the API emits at least one redacted local stderr warning

### Requirement: Sensitive Data Redaction

API logging SHALL prevent sensitive data from being written to files or stderr warnings.

#### Scenario: Sensitive fields are redacted

- **WHEN** a log record contains fields whose names or sources include authorization, cookie, csrf, password, token, secret, session, api key, or database URL material
- **THEN** the log output redacts or omits those values
- **AND** tests cover representative sensitive field names and header names

#### Scenario: Access logs do not include query string by default

- **WHEN** a request URL contains a query string
- **THEN** the access log records the path without the raw query string
- **AND** query values are not written unless a future change defines a whitelist redaction policy

#### Scenario: Actor identity is limited by stream

- **WHEN** ordinary access, app, or error records are emitted
- **THEN** they may include `actor_type`
- **AND** they do not include `actor_id` by default
- **WHEN** security or audit event records are emitted
- **THEN** they may include `actor_id` when needed for investigation

### Requirement: Maintenance Compression Retention And Disk Guard

API logging SHALL provide stage 2 maintenance for closed files without changing stage 1 core contracts.

#### Scenario: Maintenance does not touch active files

- **WHEN** maintenance compresses, cleans, or scans log files
- **THEN** it only processes closed files
- **AND** it does not compress, delete, or rewrite the active file currently used by a writer
- **AND** compression and cleanup do not run in the normal request path
- **AND** files that cannot be confidently classified as closed are skipped

#### Scenario: Closed files may be compressed

- **WHEN** a rotated file is closed and eligible for compression
- **THEN** maintenance may compress it to `.jsonl.gz`
- **AND** the compressed file remains associated with the original stream and time slice

#### Scenario: Retention is stream specific

- **WHEN** maintenance applies retention
- **THEN** retention days are configurable per stream
- **AND** access logs can have shorter retention than error, security, and audit logs

#### Scenario: Disk guard degrades access before critical streams

- **WHEN** configured total log size or free disk thresholds are exceeded
- **THEN** the API degrades access logging before dropping error, security, or audit records
- **AND** supported configuration includes `LOG_MAX_TOTAL_BYTES`, `LOG_MIN_FREE_BYTES`, `LOG_ACCESS_DROP_WHEN_FULL`, and `LOG_MAINTENANCE_MIN_AGE_SECONDS` or equivalent settings
- **AND** the API emits a redacted local stderr warning when disk guard degradation begins

### Requirement: Documentation And Validation

The change SHALL update documentation and tests so the logging contract is reviewable.

#### Scenario: Documentation explains file logging operations

- **WHEN** the change is implemented
- **THEN** `apps/api/README.md` and environment examples describe supported logging settings
- **AND** they document stream names, file layout, file naming, rotation, compression, retention, disk guard behavior, and non-goals

#### Scenario: Tests use temporary log directories

- **WHEN** automated tests validate file logging behavior
- **THEN** they use temporary directories
- **AND** they do not write test logs into the real `runtime/` directory
- **AND** the API test command `cd apps/api && uv run python -m unittest discover -s src` covers the relevant behavior

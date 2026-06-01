# api-log-file-reduction-runtime-defaults Specification

## Purpose
TBD - created by archiving change reduce-api-log-files-and-stabilize-runtime-defaults. Update Purpose after archive.
## Requirements
### Requirement: API log files rotate by day and size

API structured file logging SHALL keep logical streams but reduce physical file count by using daily time slices instead of hourly time slices.

#### Scenario: Log file names use daily slices

- **WHEN** the API writes a structured file log record
- **THEN** the record is still routed to `LOG_DIR/{stream}/YYYY/MM/DD/`
- **AND** supported logical streams remain `access`, `app`, `error`, `security`, and `audit`
- **AND** the active file name follows `{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDD}[.part-NNN].jsonl`
- **AND** the file name no longer contains an hourly `YYYYMMDDTHH` slice
- **AND** route name, actor, source, status code, and event type remain JSON fields rather than physical file name segments

#### Scenario: Same-day records share the same base file until size rotation

- **WHEN** two records for the same stream are emitted on the same UTC date but in different hours
- **AND** they belong to the same `{service, env, instance_id, pid, stream, date}` writer identity
- **THEN** the writer keeps using the same daily base file unless size rotation is required
- **AND** when the current file exceeds `LOG_ROTATE_MAX_BYTES`
- **THEN** the writer switches to the next `.part-NNN` file for the same date

#### Scenario: Process identity still separates daily files

- **WHEN** two API processes or two restarts write the same stream on the same UTC date with different `pid` values
- **THEN** their active file names remain separated by `pid`
- **AND** `.part-NNN` remains only the size-rotation suffix within one process-specific daily writer identity

#### Scenario: Date change opens a new daily file

- **WHEN** a record for a stream is emitted on a later UTC date than the current active file
- **THEN** the writer closes the previous active file
- **AND** opens a new daily file for the new date

### Requirement: Maintenance handles daily log files conservatively

API log maintenance SHALL compress and clean daily log files without touching files that might still be active.

#### Scenario: Current-day files are skipped unless force closed

- **WHEN** maintenance scans log files
- **AND** a file belongs to the current UTC date
- **THEN** maintenance treats it as not confidently closed
- **AND** does not compress or delete it
- **AND** shutdown cleanup may process it only when the writer has closed the file and passes it as a force-closed path

#### Scenario: Closed daily files are compressed and retained by stream

- **WHEN** a daily log file is older than the maintenance safety window and not active
- **THEN** maintenance may compress it to `.jsonl.gz`
- **AND** retention continues to apply per stream
- **AND** `access` logs can have shorter retention than `app`, `error`, `security`, and `audit`

### Requirement: Access log retention defaults to three days

API logging SHALL default access log retention to a short diagnostic window.

#### Scenario: Default access retention is three days

- **WHEN** `LOG_ACCESS_RETENTION_DAYS` is not explicitly configured
- **THEN** `quantagent.api.config.settings.Settings` resolves it to `3`
- **AND** defaults for `LOG_APP_RETENTION_DAYS`, `LOG_ERROR_RETENTION_DAYS`, `LOG_SECURITY_RETENTION_DAYS`, and `LOG_AUDIT_RETENTION_DAYS` remain `14`, `30`, `30`, and `90`

### Requirement: Default runtime directory is stable when not explicitly configured

QuantAgent shared settings SHALL avoid cwd-dependent runtime drift when no runtime directory override is provided.

#### Scenario: Missing or blank runtime override uses repository root runtime

- **WHEN** `RUNTIME_DIR` is not provided by constructor input, dotenv, or real process environment
- **OR** `RUNTIME_DIR` is provided as an empty string by constructor input, dotenv, or real process environment
- **AND** the source checkout repository root can be discovered
- **THEN** `quantagent.core.config.settings.Settings` resolves `RUNTIME_DIR` to `<repo-root>/runtime`
- **AND** API default `LOG_DIR` resolves to `<repo-root>/runtime/logs/api` when `LOG_DIR` is also not provided

#### Scenario: Explicit runtime override is preserved

- **WHEN** `RUNTIME_DIR` is explicitly configured as an absolute path
- **THEN** settings preserve that path
- **WHEN** `RUNTIME_DIR` is explicitly configured as a non-empty relative path
- **THEN** settings preserve cwd-relative semantics
- **AND** API default `LOG_DIR` is derived from that explicit `RUNTIME_DIR`

#### Scenario: Explicit log directory still has highest priority

- **WHEN** `LOG_DIR` is explicitly configured
- **THEN** API logging uses that directory after absolute path resolution
- **AND** it does not replace the value with `RUNTIME_DIR/logs/api`

### Requirement: Documentation reflects local defaults and production overrides

API runtime documentation SHALL distinguish local defaults from production deployment recommendations.

#### Scenario: README and env templates describe daily logs and runtime defaults

- **WHEN** the change is implemented
- **THEN** `apps/api/README.md` describes daily file naming, size rotation, stream retention, and 3-day default access retention
- **AND** documentation states that empty `RUNTIME_DIR` and `LOG_DIR` default to repository root `runtime/logs/api` for source checkout execution
- **AND** documentation states that non-empty relative `RUNTIME_DIR` values keep cwd-relative semantics
- **AND** production documentation recommends explicitly setting `RUNTIME_DIR` or `LOG_DIR` to a persistent volume path
- **AND** stdout-only structured logging is documented as a non-goal of this change

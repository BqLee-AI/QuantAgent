## ADDED Requirements

### Requirement: Plugin Manifest Is The Registry Source

QuantAgent SHALL use `plugin.yaml` as the Plugin Registry V1 source of truth for official and runtime plugins.

#### Scenario: Official and runtime plugin directories are scanned
- **WHEN** the Registry scans for plugins
- **THEN** it reads plugin manifests from `plugins/**/plugin.yaml`
- **AND** it reads plugin manifests from `runtime/plugins/**/plugin.yaml` when the runtime directory exists
- **AND** a missing `runtime/plugins` directory is treated as an empty plugin source

#### Scenario: Directories without plugin manifest are ignored
- **WHEN** the Registry encounters directories under plugin roots that do not contain `plugin.yaml`
- **THEN** those directories are ignored
- **AND** their absence does not create failed plugin records

#### Scenario: Entry point is metadata only in V1
- **WHEN** a manifest declares an `entrypoint`
- **THEN** the Registry validates that the field exists and is non-empty
- **AND** the Registry does not import, instantiate, or execute that entrypoint in V1

### Requirement: Plugin Manifest Validation Is Structured

The Registry SHALL validate plugin manifests into structured records without letting one invalid plugin break the full scan.

#### Scenario: Valid placeholder plugin is discovered
- **WHEN** the Registry scans `plugins/sources/placeholder-source/plugin.yaml`
- **THEN** it returns a plugin record with id `quantagent.official.source.placeholder`
- **AND** the record includes type, version, capabilities, config schema path, source, path and status

#### Scenario: Required manifest fields are enforced
- **WHEN** a manifest omits any of `id`, `name`, `type`, `version`, `entrypoint`, `capabilities` or `config_schema`
- **THEN** the corresponding plugin record is marked `invalid`
- **AND** `last_error` explains the missing or invalid field

#### Scenario: Config schema file must exist
- **WHEN** a manifest references `config_schema`
- **THEN** the referenced JSON Schema file must exist under the plugin directory
- **AND** a missing schema marks the plugin record `invalid`
- **AND** the full scan continues for other plugins

#### Scenario: Unknown plugin type is rejected
- **WHEN** a manifest declares a type outside the supported V1 type set
- **THEN** the plugin record is marked `invalid`
- **AND** `last_error` contains a structured unknown type summary

### Requirement: Plugin Types Use Canonical Trade Executor Naming

The Registry SHALL use canonical plugin type names and preserve a compatibility path for historical executor manifests.

#### Scenario: Executor alias is normalized
- **WHEN** a manifest declares `type: executor`
- **THEN** the Registry may accept it as a compatibility alias
- **AND** the canonical type exposed by the Registry is `trade_executor`
- **AND** this compatibility does not enable real trade execution

#### Scenario: Supported V1 plugin types are explicit
- **WHEN** the Registry validates plugin type
- **THEN** supported canonical types are `source`, `industry`, `strategy`, `notification` and `trade_executor`
- **AND** unsupported types are reported as invalid

### Requirement: Registry Scan Failures Stay Local

The Registry SHALL keep plugin scan failures local to the affected plugin record.

#### Scenario: Malformed YAML does not abort the full scan
- **WHEN** one plugin manifest cannot be parsed as YAML
- **THEN** that plugin result is represented as `invalid` or `failed`
- **AND** other valid plugins are still returned

#### Scenario: Duplicate plugin id is reported
- **WHEN** two manifests declare the same plugin id
- **THEN** the Registry marks the conflict in affected plugin records
- **AND** V1 does not attempt dependency solving or version selection

#### Scenario: Errors are safe for API responses
- **WHEN** a plugin record contains `last_error`
- **THEN** the error contains structured code, message, stage and details suitable for API responses
- **AND** it does not expose secrets, stack traces or local environment values

### Requirement: Minimal Plugin Status Model Exists

The Registry SHALL expose a minimal V1 status model for discovery and management state without implying plugin code execution.

#### Scenario: V1 status values are bounded
- **WHEN** a plugin record is returned by the Registry
- **THEN** its status is one of `discovered`, `valid`, `invalid`, `enabled`, `disabled` or `failed`

#### Scenario: Enabled does not mean loaded
- **WHEN** a plugin is marked `enabled` in V1
- **THEN** that state only represents management configuration
- **AND** it does not imply the plugin entrypoint was imported
- **AND** it does not imply `load`, `start`, scheduler subscription or tool registration happened

### Requirement: Plugin Management API Is A Thin Boundary

The API SHALL expose a minimal protected plugin management surface backed by the core Registry.

#### Scenario: Plugin list endpoint returns envelope
- **WHEN** an authenticated caller requests `GET /api/v1/plugins`
- **THEN** the API returns a standard `ApiResponse` envelope
- **AND** the data contains plugin records produced by the core Registry

#### Scenario: Plugin detail endpoint returns one record
- **WHEN** an authenticated caller requests `GET /api/v1/plugins/{plugin_id}`
- **THEN** the API returns the matching plugin record in a standard envelope
- **AND** an unknown plugin id returns the existing not found envelope pattern

#### Scenario: Config schema endpoint returns manifest schema
- **WHEN** an authenticated caller requests `GET /api/v1/plugins/{plugin_id}/config-schema`
- **THEN** the API returns the plugin config JSON Schema referenced by the manifest
- **AND** the route does not import or instantiate the plugin entrypoint

#### Scenario: Rescan endpoint refreshes registry view
- **WHEN** an authenticated caller requests `POST /api/v1/plugins/actions/rescan`
- **THEN** the API invokes the Registry scanner
- **AND** the response includes a scan summary and standard envelope
- **AND** the route does not install dependencies, hot reload plugin code or execute plugin hooks

### Requirement: Plugin Registry V1 Defers Runtime Execution

Plugin Registry V1 SHALL defer runtime execution, dependency installation and high-risk action capabilities to later changes.

#### Scenario: No dependency auto-install occurs
- **WHEN** a manifest declares plugin, Python or system dependencies
- **THEN** V1 may preserve that metadata
- **AND** V1 does not install missing dependencies automatically

#### Scenario: No real trade execution occurs
- **WHEN** a plugin declares `trade_executor` capabilities
- **THEN** V1 treats those capabilities as metadata only
- **AND** V1 does not expose real order execution, broker adapter calls or live trading actions

#### Scenario: Source sample is deferred to V1.1
- **WHEN** implementation work begins after this OpenSpec is approved
- **THEN** the initial implementation focuses on Registry, API and diagnostics
- **AND** a pull source sample and RawEvent production path are handled by a later change or follow-up implementation phase

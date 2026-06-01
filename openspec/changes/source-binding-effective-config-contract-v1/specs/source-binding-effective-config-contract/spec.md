## ADDED Requirements

### Requirement: Platform SHALL normalize a source binding template contract before any persistence or scheduling

The platform SHALL normalize each source binding declaration into a `SourceBindingTemplate` contract before persistence, scheduling, API exposure, or plugin invocation can consume it.

#### Scenario: Normalized template keeps only declarative binding fields

- **WHEN** the platform loads a source binding declaration from an industry package asset or future control-plane input
- **THEN** it MUST normalize the declaration into a `SourceBindingTemplate`
- **AND** the normalized template MUST contain `source_plugin_id` and `required`
- **AND** the normalized template MAY contain `config_template_ref`, `config_override`, `schedule_policy_hint`, `retry_policy_hint`, `rate_limit_policy_hint`, and JSON-safe `metadata`
- **AND** the normalized template MUST NOT contain run status, ORM identifiers, request identifiers, plugin output payloads, or resolved secret values

#### Scenario: Template references stay opaque at contract level

- **WHEN** a source binding declaration references a reusable config template asset
- **THEN** the contract MUST preserve that reference as an opaque `config_template_ref`
- **AND** the contract MUST NOT hardcode industry package directory layout or file path rules in this capability
- **AND** downstream asset organization MAY be defined by a separate capability without changing merge semantics

### Requirement: Platform SHALL synthesize an auditable effective source config with deterministic precedence

The platform SHALL synthesize an `EffectiveSourceConfig` snapshot from source defaults, template references, inline overrides, and platform-managed metadata using deterministic precedence rules.

#### Scenario: Merge order is deterministic and platform-owned

- **WHEN** the platform synthesizes one effective source config
- **THEN** it MUST apply source plugin defaults before template asset content
- **AND** it MUST apply template asset content before `config_override`
- **AND** it MUST apply platform-generated metadata after all user-authored config layers
- **AND** no plugin, scheduler, API router, or persistence adapter may redefine that precedence

#### Scenario: Policy objects stay outside source-specific config

- **WHEN** the platform emits an `EffectiveSourceConfig`
- **THEN** source-specific values MUST live under `config`
- **AND** `schedule_policy`, `retry_policy`, and `rate_limit_policy` MUST remain separate top-level policy objects
- **AND** policy fields MUST NOT be flattened into source-specific `config`

### Requirement: Platform SHALL reject invalid or unknown effective-config input before runtime execution

The platform SHALL validate template input and synthesized effective config before any runtime invocation can use it.

#### Scenario: Unknown override fields fail validation

- **WHEN** a template reference or `config_override` contains fields not allowed by the source plugin schema or platform policy schemas
- **THEN** synthesis MUST fail before persistence or scheduling uses that config
- **AND** the platform MUST NOT silently preserve unknown fields for later runtime execution

#### Scenario: Only JSON-safe values can cross the template and snapshot boundary

- **WHEN** a template, policy object, or synthesized effective config is accepted by the platform
- **THEN** all values MUST be JSON-safe
- **AND** those values MUST NOT include database sessions, ORM models, internal services, scheduler instances, secret resolvers, or other host-only objects
- **AND** `null` overrides MUST only be accepted when the governing schema explicitly allows them

### Requirement: Platform SHALL keep secret references auditable and runtime secret resolution ephemeral

The platform SHALL separate auditable secret references from runtime-resolved secret material.

#### Scenario: Effective source config stores only secret references

- **WHEN** a source binding template contains sensitive values
- **THEN** the platform MUST store and audit those values as structured secret references rather than plaintext
- **AND** the resulting `EffectiveSourceConfig` MUST retain secret references instead of resolved secret material
- **AND** the platform MUST be able to compute audit metadata such as validation time and fingerprint without exposing secret plaintext

#### Scenario: Runtime resolves secrets without changing the auditable snapshot

- **WHEN** the runtime prepares to invoke a source plugin
- **THEN** it MAY resolve secret references into a runtime-only execution object
- **AND** that resolved execution object MUST NOT become the persisted or publicly exposed `EffectiveSourceConfig`
- **AND** scheduler, persistence, and non-runtime consumers MUST continue using the auditable snapshot rather than resolved secret values

### Requirement: Plugins SHALL consume platform-generated effective config and MUST NOT own config synthesis

Source plugins MUST consume the platform-generated validated config and MUST NOT own template normalization, override synthesis, or secret-resolution policy.

#### Scenario: Plugin invocation uses validated platform config

- **WHEN** the platform invokes a source plugin
- **THEN** it MUST pass validated effective config through the platform-owned runtime DTO path
- **AND** the plugin MUST treat that config as input rather than a value it recomputes
- **AND** the plugin MUST NOT read binding defaults, template assets, or secret stores directly to reconstruct effective config

#### Scenario: Downstream systems reuse one effective-config truth

- **WHEN** persistence, scheduler, API, and industry package tooling interact around the same source binding
- **THEN** they MUST align to the same `SourceBindingTemplate` and `EffectiveSourceConfig` contract defined by the platform
- **AND** none of those systems may introduce a second merge algorithm or a second effective-config truth source

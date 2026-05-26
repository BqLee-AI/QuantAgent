## ADDED Requirements

### Requirement: 多个模型供应商配置可管理

QuantAgent SHALL provide a multi-provider model configuration surface where users can manage multiple OpenAI-compatible provider records instead of a single global config object.

#### Scenario: Query provider list
- **WHEN** an authenticated caller requests `GET /api/v1/models/providers`
- **THEN** the API returns a standard envelope containing multiple provider summaries
- **AND** each summary includes provider id, provider type, display name, enabled flag, default flag, key status, masked key state, model count, last error, and updated timestamp
- **AND** the response does not include API key plaintext values

#### Scenario: Provider list supports search and state filtering in Web
- **WHEN** a user opens the Web models page with many provider records
- **THEN** the provider list supports keyword search
- **AND** the page supports at least these state filters: all, enabled, default, failed, and missing key

#### Scenario: Create provider config
- **WHEN** an authenticated caller creates a provider with display name, base URL, enabled flag, and API key
- **THEN** QuantAgent stores a new provider record
- **AND** the API response returns non-secret provider fields only

#### Scenario: Update provider config
- **WHEN** an authenticated caller updates an existing provider
- **THEN** QuantAgent updates the target provider record without requiring the old API key plaintext
- **AND** a newly supplied API key replaces the stored encrypted key

#### Scenario: Create provider from preset template
- **WHEN** a user creates a provider from a Web preset template such as OpenAI, Anthropic, DeepSeek, Qwen, Moonshot, OpenRouter, or custom OpenAI-compatible
- **THEN** the page pre-fills recommended provider name, base URL, and example model values
- **AND** the user can still edit those fields before saving

### Requirement: 一个默认 provider 可被选择

QuantAgent SHALL allow one configured provider to be marked as the default provider for runtime use.

#### Scenario: Set default provider
- **WHEN** an authenticated caller requests the set-default action for a provider
- **THEN** QuantAgent marks that provider as default
- **AND** no other provider remains marked as default

#### Scenario: Default provider is visible in list
- **WHEN** a user views the models page or provider list API
- **THEN** the current default provider is explicitly indicated

### Requirement: Provider 下模型可被独立管理

QuantAgent SHALL allow each provider to manage multiple runtime model records instead of a single embedded model string.

#### Scenario: Add provider model
- **WHEN** an authenticated caller adds a model under a provider
- **THEN** QuantAgent stores a provider-scoped model record with enabled state
- **AND** the response returns provider model metadata without secret fields

#### Scenario: Mark one global default model
- **WHEN** an authenticated caller marks one provider model as the global default model
- **THEN** QuantAgent keeps that model as the single global default
- **AND** no other provider model remains marked as global default

#### Scenario: Multimodal capability can be declared
- **WHEN** a provider model is created or updated
- **THEN** QuantAgent supports at least a `supports_vision` capability flag for that model

### Requirement: 固定任务模型类别必须可预设

QuantAgent SHALL provide system-defined model preset categories that are fixed by product code and not editable by end users.

#### Scenario: Query fixed preset categories
- **WHEN** an authenticated caller requests `GET /api/v1/models/presets`
- **THEN** the API returns the fixed preset categories
- **AND** the set includes `global_default`, `economy_text`, `general_text`, `reasoning_text`, and `multimodal`

#### Scenario: User binds one preset to a chosen model
- **WHEN** an authenticated caller updates one preset binding
- **THEN** QuantAgent stores the selected primary model binding for that preset
- **AND** the response returns preset key, current primary model, fallback model, and validation status

#### Scenario: Users cannot create arbitrary preset categories
- **WHEN** a caller attempts to create, rename, or delete a preset category
- **THEN** QuantAgent rejects that operation because preset categories are system-defined

### Requirement: 基础 fallback 必须存在且顺序固定

QuantAgent SHALL provide a minimal fixed fallback mechanism for system model preset resolution.

#### Scenario: Resolve preset primary model first
- **WHEN** a runtime flow resolves a preset such as `economy_text`
- **THEN** QuantAgent first attempts the preset primary model

#### Scenario: Resolve preset fallback model second
- **WHEN** the preset primary model is unavailable or fails before a successful invocation
- **THEN** QuantAgent attempts the preset fallback model when one is configured

#### Scenario: Resolve global default model last
- **WHEN** the preset primary model and preset fallback model are both unavailable or fail
- **THEN** QuantAgent attempts the global default model when capability constraints remain compatible

#### Scenario: Multimodal preset cannot fallback to non-vision model
- **WHEN** the preset key is `multimodal`
- **THEN** QuantAgent SHALL NOT fallback to a model whose `supports_vision` flag is false

### Requirement: Provider API keys remain encrypted and write-only

QuantAgent SHALL continue storing provider API keys encrypted at rest and SHALL NOT expose plaintext keys through API responses, logs, errors, or frontend state.

#### Scenario: Provider list shows masked key only
- **WHEN** a frontend page loads provider summaries or provider detail
- **THEN** the page can show that a key is configured or masked
- **AND** the old API key plaintext is never returned by the API

#### Scenario: Missing encryption key is reported safely
- **WHEN** the server cannot encrypt or decrypt provider API keys because `MODEL_CONFIG_ENCRYPTION_KEY` is not configured
- **THEN** the API returns a structured configuration error
- **AND** the response does not include provider API key plaintext, encryption key, stack trace, or provider request payload

### Requirement: 每个 provider 可独立测试连接

QuantAgent SHALL provide a test connection action for each configured provider using a fixed smoke prompt.

#### Scenario: Test one provider successfully
- **WHEN** an authenticated caller requests `POST /api/v1/models/providers/{provider_id}/actions/test-connection`
- **THEN** QuantAgent sends only the fixed smoke prompt to that provider
- **AND** the API returns success status, provider id, provider name, model, token usage when available, and request id

#### Scenario: Disabled provider test is blocked
- **WHEN** a caller requests test connection for a disabled provider
- **THEN** QuantAgent does not call the provider
- **AND** the API returns a structured disabled-provider error

#### Scenario: Missing-key provider test is blocked
- **WHEN** a caller requests test connection for a provider without a configured key
- **THEN** QuantAgent does not call the provider
- **AND** the API returns a structured missing-key error

### Requirement: Invocation usage is关联到具体 provider 和 preset

QuantAgent SHALL record model invocation summaries against the specific provider record and preset context that were used.

#### Scenario: Invocation log includes provider reference
- **WHEN** a smoke test or later runtime call completes
- **THEN** the invocation summary records provider id, provider name, model, status, token usage, created timestamp, request id, and trace id when available

#### Scenario: Invocation log can include preset key
- **WHEN** a runtime call is made through one of the fixed preset categories
- **THEN** the invocation summary records the `preset_key` that resolved the model when available

#### Scenario: Invocation list can be filtered by provider or preset
- **WHEN** an authenticated caller requests recent invocations for a specific provider or preset
- **THEN** QuantAgent returns recent invocation summaries scoped to that provider or preset when `provider_id` or `preset_key` filter is supplied

### Requirement: Web exposes provider management plus preset workflow

QuantAgent Web SHALL provide a multi-provider configuration page shaped like a standard software provider management screen and a separate fixed preset assignment workflow.

#### Scenario: Web shows provider list and selected detail
- **WHEN** a user opens `/models`
- **THEN** the page shows a provider list with default/enabled/error/key indicators
- **AND** selecting a provider reveals its detail form and usage panel

#### Scenario: Web offers preset and custom provider creation
- **WHEN** a user starts creating a new provider
- **THEN** the page offers preset templates and a custom OpenAI-compatible option
- **AND** the creation flow does not force the user into a blank raw form as the only entry path

#### Scenario: Web shows fixed preset assignment view
- **WHEN** a user opens the preset tab or preset section
- **THEN** the page shows the fixed categories `global_default`, `economy_text`, `general_text`, `reasoning_text`, and `multimodal`
- **AND** each category shows current primary model, fallback model, and validation status

#### Scenario: Web supports create and set default
- **WHEN** a user creates a new provider, marks one as default, or marks one provider model as the global default model
- **THEN** the page updates the provider list and preset view without exposing key plaintext

#### Scenario: Web shows standard management states
- **WHEN** provider data or preset data is loading, missing, failing, or permission-protected
- **THEN** the page shows loading, empty, error, validation, and permission-aware states with safe request id display when applicable

### Requirement: 本轮仍不进入完整 provider governance

This V1 change SHALL improve provider management shape and preset routing basics without implementing the full ProviderPolicy governance platform.

#### Scenario: ProviderPolicy editor is still excluded
- **WHEN** this change is implemented
- **THEN** it does not introduce user-editable `fast`, `balanced`, `reasoning`, `local`, visual fallback chain editing, budget limit editing, or cost governance

#### Scenario: Non-provider surfaces do not own model keys
- **WHEN** users configure provider credentials
- **THEN** model keys remain managed through the model provider APIs and models page
- **AND** ordinary Settings and plugin config do not become model API key storage surfaces

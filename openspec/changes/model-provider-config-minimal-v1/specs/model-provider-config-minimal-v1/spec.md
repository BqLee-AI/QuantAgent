## ADDED Requirements

### Requirement: 全局模型配置可保存和查询

QuantAgent SHALL provide one global OpenAI-compatible model configuration for the minimal V1 model runtime path.

#### Scenario: Query empty model config
- **WHEN** an authenticated caller requests `GET /api/v1/models/config` before any API key is configured
- **THEN** the API returns a standard envelope with `provider_type` equal to `openai_compatible`
- **AND** the response includes configuration status such as `missing_key` or equivalent key status
- **AND** the response does not include an API key plaintext value

#### Scenario: Save global model config
- **WHEN** an authenticated caller sends `PUT /api/v1/models/config` with provider display name, base URL, model, enabled flag, and API key
- **THEN** QuantAgent stores the global model configuration
- **AND** the API response returns the saved non-secret configuration fields
- **AND** the API response does not include the API key plaintext value

#### Scenario: Query configured model config
- **WHEN** an authenticated caller requests `GET /api/v1/models/config` after a key has been saved
- **THEN** the API response includes provider type, provider display name, base URL, model, enabled flag, key status, masked key state, last error, and updated timestamp
- **AND** the API response does not include an API key plaintext value

### Requirement: API key is encrypted at rest

QuantAgent SHALL store model provider API keys encrypted at rest and SHALL NOT expose plaintext keys through API responses, logs, errors, or frontend state.

#### Scenario: API key is encrypted before persistence
- **WHEN** a model API key is saved through the model config API
- **THEN** the persisted database value is encrypted before storage
- **AND** the database does not store the directly readable plaintext key

#### Scenario: API key query is write-only from the frontend perspective
- **WHEN** a frontend page loads an already configured model config
- **THEN** the frontend can show that a key is configured or masked
- **AND** the frontend cannot read the old API key plaintext from the API

#### Scenario: Missing encryption key is reported safely
- **WHEN** the server cannot encrypt or decrypt model API keys because the service encryption key is not configured
- **THEN** the API returns a structured configuration error
- **AND** the error response does not include the model API key, encryption key, stack trace, or provider request payload

#### Scenario: Logs do not leak key plaintext
- **WHEN** model config save, query, test connection, or invocation recording fails
- **THEN** logs and structured error summaries do not contain the API key plaintext

### Requirement: Saved config can run a fixed smoke model call

QuantAgent SHALL provide a test connection action that uses the saved model configuration to execute a fixed smoke prompt.

#### Scenario: Test connection succeeds
- **WHEN** an authenticated caller requests `POST /api/v1/models/actions/test-connection` and the saved configuration is enabled with a valid key and model
- **THEN** QuantAgent sends only the fixed smoke prompt to the configured OpenAI-compatible provider
- **AND** the API returns success status, provider, model, token usage if available, and request id
- **AND** the API response does not include the full provider response body

#### Scenario: Test connection is blocked when disabled
- **WHEN** an authenticated caller requests test connection while the global model config is disabled
- **THEN** QuantAgent does not call the provider
- **AND** the API returns a structured disabled configuration error

#### Scenario: Test connection is blocked when key is missing
- **WHEN** an authenticated caller requests test connection while no API key is configured
- **THEN** QuantAgent does not call the provider
- **AND** the API returns a structured missing key error

#### Scenario: Test connection prompt is fixed
- **WHEN** a caller requests the test connection action
- **THEN** the action does not accept or forward caller-provided prompt text
- **AND** it does not send real events, trading context, private strategy, full prompt content, or sensitive runtime context

### Requirement: Model invocations record token usage

QuantAgent SHALL record model invocation summaries in an independent invocation log.

#### Scenario: Successful invocation records token usage
- **WHEN** a smoke test or later model runtime call completes successfully
- **THEN** QuantAgent records provider, model, status, prompt tokens, completion tokens, total tokens, created timestamp, request id, and trace id when available
- **AND** the invocation record can optionally link to an AgentRun through `agent_run_id`

#### Scenario: Failed invocation records a safe error summary
- **WHEN** a model provider call fails because of authentication, timeout, unavailable model, provider error, or invalid configuration
- **THEN** QuantAgent records a failed invocation summary
- **AND** the error summary does not include API key plaintext, full prompt text, full provider response, stack trace, or sensitive runtime context

#### Scenario: Token usage can be absent
- **WHEN** an OpenAI-compatible provider response does not include token usage
- **THEN** QuantAgent still records provider, model, status, timestamp, and request id
- **AND** missing token counts are represented without inventing token values

#### Scenario: Invocation list returns recent usage
- **WHEN** an authenticated caller requests `GET /api/v1/models/invocations`
- **THEN** the API returns recent invocation summaries in a standard envelope
- **AND** each summary includes provider, model, status, token usage fields, created timestamp, and request id when available

### Requirement: Web exposes minimal model config and token usage

QuantAgent Web SHALL provide a minimal model configuration entry for configuring the global model provider and viewing basic invocation usage.

#### Scenario: Web form saves model config
- **WHEN** a user opens the model configuration page
- **THEN** the page provides controls for provider type, display name, base URL, model, API key, and enabled flag
- **AND** saving the form calls the model config API instead of storing model secrets in frontend runtime config

#### Scenario: Web shows masked key status
- **WHEN** a model API key has already been configured
- **THEN** the page shows a masked or configured key state
- **AND** the API key input behaves as a write-only replacement field
- **AND** the page does not display the old API key plaintext

#### Scenario: Web shows test connection states
- **WHEN** a user runs the model connection test
- **THEN** the page shows running, success, or failed state
- **AND** failed state shows a safe error summary and request id when available

#### Scenario: Web shows basic token usage
- **WHEN** recent model invocations exist
- **THEN** the page displays provider, model, status, prompt tokens, completion tokens, total tokens, created timestamp, and recent error summary when available

### Requirement: V1 excludes complete provider governance

Model provider config minimal V1 SHALL NOT implement full model governance features.

#### Scenario: ProviderPolicy is not introduced
- **WHEN** this V1 change is implemented
- **THEN** it does not introduce ProviderPolicy, `fast`, `balanced`, `reasoning`, or `local` policy selection
- **AND** AgentDefinition still cannot bind API keys directly

#### Scenario: Fallback and budget are not introduced
- **WHEN** this V1 change is implemented
- **THEN** it does not implement fallback models, budget limits, cost governance, automatic model discovery, or LiteLLM Proxy deployment

#### Scenario: Settings and plugin config do not own model keys
- **WHEN** users configure model provider credentials
- **THEN** model keys are managed through the model config API and model page
- **AND** ordinary Settings and plugin config do not become model API key storage surfaces

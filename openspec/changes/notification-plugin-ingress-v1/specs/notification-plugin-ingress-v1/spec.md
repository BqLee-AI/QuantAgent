## ADDED Requirements

### Requirement: Notification ingress uses a host-orchestration-plugin split

QuantAgent SHALL separate notification ingress into three layers:

- transport host
- core notification ingress orchestration
- notification plugin protocol adapter

#### Scenario: transport host only terminates transport protocol
- **WHEN** an external notification platform sends a webhook, interaction callback, websocket event, or polling-delivered input
- **THEN** the transport host receives the external input
- **AND** extracts transport-safe request data
- **AND** passes a typed receive input to platform orchestration
- **AND** does not directly parse channel-specific business payload semantics as the long-term architecture truth

#### Scenario: HTTP host is only one adapter form
- **WHEN** the current implementation handles Discord
- **THEN** `apps/api` may host the HTTP route
- **AND** that HTTP route is only one concrete transport host adapter
- **AND** the architecture remains extensible to websocket and polling transports

#### Scenario: core orchestration owns business handoff
- **WHEN** a typed notification receive request reaches platform orchestration
- **THEN** orchestration validates plugin selection and capability
- **AND** invokes the plugin through runtime
- **AND** validates the receive result
- **AND** decides record / audit / topic / approval handoff behavior
- **AND** the plugin itself does not become the business-state coordinator

### Requirement: `notification.receive` has a typed input contract

Notification Plugin Ingress V1 SHALL define a stable typed input contract for `notification.receive`.

#### Scenario: receive input can be constructed without FastAPI objects
- **WHEN** a caller, test harness, or API adapter constructs a `notification.receive` invocation
- **THEN** it can use a typed `NotificationReceiveInput`
- **AND** that DTO does not require FastAPI `Request`
- **AND** that DTO does not require FastAPI `Response`
- **AND** that DTO does not require a socket, raw transport object, or host framework instance

#### Scenario: receive input captures safe HTTP ingress fields
- **WHEN** a typed `NotificationReceiveInput` is constructed
- **THEN** it supports at least:
  - `transport`
  - `headers`
  - `body_text` or equivalent safe body representation
  - `query_params`
  - `path_params`
  - `request_metadata`
  - optional `config_override`
- **AND** all DTO fields are JSON-safe
- **AND** all DTO fields follow plugin-sdk read-only / frozen semantics

#### Scenario: receive input identifies transport kind
- **WHEN** a typed `NotificationReceiveInput` is constructed
- **THEN** it identifies the transport kind through a stable field such as `transport`
- **AND** that field can distinguish at least webhook-style, websocket-style, and polling-style host adapters
- **AND** the DTO contract is not HTTP-only by design

#### Scenario: receive input does not expose privileged host capabilities
- **WHEN** a plugin receives `NotificationReceiveInput`
- **THEN** it does not gain access to DB session
- **AND** it does not gain access to Event Bus publisher
- **AND** it does not gain access to secret resolver
- **AND** it does not gain access to internal service locator behavior

### Requirement: Notification plugins remain protocol adapters

Notification plugins SHALL remain channel protocol adapters for both send and receive paths.

#### Scenario: send path remains plugin-owned protocol adaptation
- **WHEN** platform code requests `notification.send`
- **THEN** the plugin maps a platform send request to a channel-specific request
- **AND** the plugin returns a standardized send result
- **AND** the plugin does not directly publish Event Bus topics
- **AND** the plugin does not directly mutate business state

#### Scenario: receive path remains plugin-owned protocol adaptation
- **WHEN** platform code requests `notification.receive`
- **THEN** the plugin validates the channel-specific request format
- **AND** the plugin parses channel-specific payload semantics
- **AND** the plugin returns a standardized `NotificationReceiveResult`
- **AND** the plugin does not directly write approval records
- **AND** the plugin does not directly publish topics
- **AND** the plugin does not directly call broker or decision flows

### Requirement: Platform orchestration validates and standardizes receive results

Core notification ingress orchestration SHALL validate receive results before they enter any later business chain.

#### Scenario: successful receive result with response only
- **WHEN** a plugin returns `accepted=true` and a valid protocol `response` but no `item`
- **THEN** orchestration treats the callback as successfully handled at the protocol layer
- **AND** it may return the response to the external platform
- **AND** it does not require approval handoff or other business-chain handoff

#### Scenario: successful receive result with standardized item
- **WHEN** a plugin returns `accepted=true` and a valid `item`
- **THEN** orchestration validates the item shape
- **AND** orchestration treats any later receive fact / audit / approval handoff as platform-owned follow-up
- **AND** orchestration decides whether that item should later enter approval, reanalysis, or other business flows

#### Scenario: invalid receive result is rejected by platform
- **WHEN** a plugin returns a malformed receive result
- **THEN** orchestration rejects it as a platform failure
- **AND** the malformed result does not silently enter later business flows

### Requirement: Notification receive facts belong to the platform, not the plugin

QuantAgent SHALL treat notification receive facts as platform-owned records or audits, not plugin-owned persistence.

#### Scenario: platform records successful receive normalization
- **WHEN** a receive result is accepted and includes a standardized item
- **THEN** the platform owns the later notification receive record / audit fact boundary
- **AND** the plugin does not itself become the persistence truth

#### Scenario: receive fact is distinct from approval completion
- **WHEN** the platform records a normalized receive fact
- **THEN** that fact does not by itself mean approval is completed
- **AND** that fact does not by itself mean a business action has been executed

### Requirement: Event Bus publication remains platform-owned

If notification receive results are published to Event Bus topics, publication SHALL remain platform-owned.

#### Scenario: plugin runtime cannot publish receive events directly
- **WHEN** a notification plugin finishes `notification.receive`
- **THEN** the plugin itself does not publish Event Bus topics
- **AND** any topic publication happens through platform orchestration

#### Scenario: receive event is distinct from later business topics
- **WHEN** the platform publishes a receive-related topic
- **THEN** the topic represents that ingress normalization has succeeded
- **AND** it is distinct from later topics such as `approval.requested` or `approval.completed`

### Requirement: Discord is a compliant sample of the general notification ingress model

Discord SHALL be refactored toward the general notification ingress model instead of remaining a long-term API-host special case.

#### Scenario: Discord protocol logic remains in the plugin
- **WHEN** Discord send or receive behavior is implemented
- **THEN** Discord-specific protocol logic such as webhook send, request signature verification, `PING`, command payload parsing, and response generation remains in the Discord plugin

#### Scenario: Discord route becomes a host adapter, not the architecture truth
- **WHEN** the API exposes a Discord webhook route
- **THEN** that route may remain public and stable
- **AND** internally it acts as an adapter to the general notification ingress orchestration
- **AND** it is not the long-term architectural truth for notification receive behavior

#### Scenario: Discord no longer defines the general host boundary
- **WHEN** future notification platforms are added
- **THEN** they can reuse the same host-orchestration-plugin split
- **AND** they do not require copying Discord-specific API service structure as the system pattern

### Requirement: V1 implementation scope remains limited to Discord-needed HTTP basics

Notification Plugin Ingress V1 SHALL keep the implementation scope narrowly aligned to Discord-needed HTTP basics, even though the model remains extensible to other transports.

#### Scenario: websocket and polling remain future implementation paths
- **WHEN** V1 is implemented
- **THEN** the model may remain extensible to websocket and polling transports
- **AND** V1 is not required to implement websocket host behavior
- **AND** V1 is not required to implement polling host behavior

#### Scenario: Discord gets only the basic interface it needs now
- **WHEN** V1 implementation work is planned
- **THEN** it focuses on the basic Discord send/receive interface needs
- **AND** it does not expand the implementation scope into generalized gateway, long-lived stream management, or polling scheduler infrastructure

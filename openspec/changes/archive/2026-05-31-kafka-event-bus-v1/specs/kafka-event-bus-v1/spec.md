## ADDED Requirements

### Requirement: Event Bus V1 defines a stable envelope contract

Kafka Event Bus V1 SHALL publish and consume events through a stable `EventEnvelope` contract instead of passing naked ORM models, API DTOs, plugin DTOs, or ad hoc dictionaries.

#### Scenario: envelope contains required metadata
- **WHEN** a platform service publishes an event
- **THEN** the envelope includes `id`
- **AND** the envelope includes `topic`
- **AND** the envelope includes `payload`
- **AND** the envelope includes `producer`
- **AND** the envelope includes `created_at`
- **AND** the envelope includes `correlation_id`
- **AND** the envelope includes `causation_id`
- **AND** the envelope includes `headers`
- **AND** the envelope includes `retry_count`
- **AND** the envelope includes `schema_version`

#### Scenario: envelope payload and headers are JSON-safe
- **WHEN** an event envelope contains `payload` or `headers`
- **THEN** both fields are JSON-like objects
- **AND** values only use JSON-safe types: string, number, boolean, null, array, or object
- **AND** the envelope does not contain a database session, ORM model, plugin instance, scheduler, internal service, secret resolver, or non-serializable object

#### Scenario: schema version starts at V1
- **WHEN** Event Bus V1 constructs an envelope
- **THEN** `schema_version` is set to `1`
- **AND** any future breaking envelope shape change requires a new OpenSpec change

### Requirement: Event Bus V1 restricts topic names through topic policy

Kafka Event Bus V1 SHALL validate event topics against a stable topic policy.

#### Scenario: default topic set is accepted
- **WHEN** a publisher validates a V1 topic
- **THEN** `source.event.captured` is accepted
- **AND** `event.routed` is accepted
- **AND** `industry.analysis.requested` is accepted
- **AND** `industry.analysis.completed` is accepted
- **AND** `analysis.scored` is accepted
- **AND** `decision.created` is accepted
- **AND** `approval.requested` is accepted
- **AND** `approval.completed` is accepted
- **AND** `notification.requested` is accepted
- **AND** `notification.completed` is accepted
- **AND** `broker.dry_run_requested` is accepted
- **AND** `broker.dry_run_completed` is accepted
- **AND** `runtime.failed` is accepted

#### Scenario: unknown topic is rejected
- **WHEN** a publisher attempts to publish an envelope with an unregistered topic
- **THEN** Event Bus V1 rejects the envelope before sending it to Kafka or the memory fake
- **AND** the rejection is represented as a structured event bus error

### Requirement: Event Bus V1 exposes publisher, consumer, handler, codec, and topic ports

Kafka Event Bus V1 SHALL expose reusable core ports so callers do not depend directly on Kafka client APIs.

#### Scenario: publisher uses core port
- **WHEN** API, worker, scheduler, or future platform services publish an event
- **THEN** they call `EventBusPublisher.publish(envelope)`
- **AND** they do not instantiate or call Kafka producer APIs directly

#### Scenario: consumer uses core port
- **WHEN** worker, scheduler, or future runtime services consume events
- **THEN** they call `EventBusConsumer.subscribe(topics, group_id, handler)`
- **AND** they provide a handler that follows the `EventBusHandler.handle(envelope)` contract
- **AND** they do not parse Kafka records directly in app entrypoints

#### Scenario: codec owns wire conversion
- **WHEN** an envelope is sent to or read from a backend
- **THEN** `EventBusCodec.encode(envelope)` owns conversion to the backend wire shape
- **AND** `EventBusCodec.decode(message)` owns conversion back to `EventEnvelope`
- **AND** backend adapters do not each define incompatible envelope serialization

### Requirement: Memory fake is the default local and test backend

Kafka Event Bus V1 SHALL support a memory-backed event bus as the default backend for tests and ordinary local development.

#### Scenario: no Kafka configuration still allows minimum startup
- **WHEN** the application starts without Kafka-specific configuration
- **THEN** Event Bus V1 uses the memory backend by default
- **AND** unit tests can publish and consume events without a running Kafka broker
- **AND** Kafka is not required for the minimum local development path

#### Scenario: memory fake follows the same contract as Kafka adapter
- **WHEN** a test publishes through the memory backend
- **THEN** the memory backend validates the envelope
- **AND** the memory backend validates topic policy
- **AND** the memory backend dispatches to subscribed handlers through the same handler contract used by the Kafka adapter

### Requirement: Kafka adapter is explicitly enabled and lives behind core ports

Kafka Event Bus V1 SHALL provide Kafka as an explicit runtime backend behind `packages/core` event bus ports.

#### Scenario: Kafka backend requires explicit selection
- **WHEN** `EVENT_BUS_BACKEND` or the equivalent settings value is set to `kafka`
- **THEN** Event Bus V1 initializes the Kafka adapter
- **AND** Kafka bootstrap server configuration is required
- **AND** missing required Kafka configuration fails readiness with a structured configuration error

#### Scenario: Kafka adapter supports minimum producer and consumer semantics
- **WHEN** Kafka backend is enabled
- **THEN** Event Bus V1 can publish envelopes through a Kafka producer
- **AND** Event Bus V1 can subscribe to topics with a consumer group
- **AND** Event Bus V1 commits or acknowledges successful handler processing
- **AND** Event Bus V1 supports graceful consumer shutdown

#### Scenario: Kafka client remains an implementation detail
- **WHEN** a caller imports or constructs Event Bus V1
- **THEN** the caller depends on `packages/core` event bus ports
- **AND** the caller does not need to import Kafka client classes

### Requirement: Plugin runtime cannot directly publish to Event Bus

Kafka Event Bus V1 SHALL preserve plugin isolation by preventing plugins from directly accessing event bus publishers or consumers.

#### Scenario: RuntimeContext excludes event bus publisher
- **WHEN** a plugin receives RuntimeContext
- **THEN** the context does not expose `event_bus`
- **AND** the context does not expose an event publisher
- **AND** the context does not expose an event consumer
- **AND** the context does not expose a database session, ORM model, scheduler, internal service, or secret resolver

#### Scenario: platform service publishes plugin output
- **WHEN** a source plugin returns typed output from Runtime invoke
- **THEN** the plugin does not publish the event itself
- **AND** a platform service validates or normalizes the typed output
- **AND** the platform service constructs an `EventEnvelope`
- **AND** the platform service publishes through `EventBusPublisher`

### Requirement: Event Bus V1 does not replace persistence or audit truth

Kafka Event Bus V1 SHALL distinguish asynchronous message distribution from business state persistence and audit recovery.

#### Scenario: event bus publish does not imply RawEvent persistence
- **WHEN** an event envelope is published successfully
- **THEN** Event Bus V1 does not claim that RawEvent has been persisted
- **AND** Event Bus V1 does not claim that Event state transition has been persisted
- **AND** Event Bus V1 does not claim that audit record has been written

#### Scenario: outbox and replay remain out of scope
- **WHEN** Event Bus V1 is implemented
- **THEN** it is not required to implement database outbox
- **AND** it is not required to implement replay
- **AND** it is not required to implement RawEvent dedupe
- **AND** it is not required to implement DLQ database records

### Requirement: App entrypoints remain composition roots only

Kafka Event Bus V1 SHALL keep protocol and event bus semantics in `packages/core`, while app entrypoints compose runtime services.

#### Scenario: worker consumes through core event bus
- **WHEN** worker support is added for event consumption
- **THEN** the worker entrypoint starts core event bus consumers or handlers
- **AND** the worker entrypoint does not define envelope fields, topic policy, or Kafka serialization

#### Scenario: scheduler publishes through platform services
- **WHEN** scheduler support is added for source or plugin scheduling
- **THEN** scheduler invokes platform services that publish through core event bus ports
- **AND** scheduler does not expose an event bus publisher to plugins

#### Scenario: API does not run long-lived consumers
- **WHEN** API support is added around Event Bus V1
- **THEN** API may expose management or health boundaries
- **AND** API does not run a long-lived event consumer loop inside request handlers

### Requirement: Event Bus V1 protects sensitive data in errors and logs

Kafka Event Bus V1 SHALL prevent secrets and sensitive local context from appearing in event bus errors, headers, payload diagnostics, and logs.

#### Scenario: event bus error summary is sanitized
- **WHEN** publish, decode, subscribe, or handler dispatch fails
- **THEN** the structured error summary does not expose secret values
- **AND** it does not expose tokens, cookies, full local private paths, full stack traces, full prompts, or private strategy text

#### Scenario: envelope diagnostics are safe for review
- **WHEN** tests or logs record envelope diagnostics
- **THEN** they may include topic, envelope id, producer, schema version, retry count, and safe error code
- **AND** they do not include raw sensitive payload fields or secret-bearing headers

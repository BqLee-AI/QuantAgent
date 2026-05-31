## ADDED Requirements

### Requirement: PluginSchedulingService accepts optional EventBusPublisher

PluginSchedulingService SHALL accept an optional `EventBusPublisher` through constructor injection. When `publisher` is `None`, the service SHALL behave identically to the current implementation with zero regression.

#### Scenario: publisher is not provided
- **GIVEN** a `PluginSchedulingService` constructed without a `publisher`
- **WHEN** `trigger()` is called with any request
- **THEN** the service SHALL execute the plugin and return a `PluginRunRecord`
- **AND** no event SHALL be published to any event bus
- **AND** the behavior SHALL be identical to the current implementation

#### Scenario: publisher is provided
- **GIVEN** a `PluginSchedulingService` constructed with a valid `EventBusPublisher`
- **WHEN** `trigger()` is called with a `source.fetch` capability request
- **AND** the plugin execution succeeds (`SUCCEEDED`)
- **THEN** the service SHALL publish a `source.event.captured` event through the publisher
- **AND** the `PluginRunRecord` SHALL still be returned as `SUCCEEDED`

### Requirement: Only source.fetch success path publishes events

Event publishing SHALL only occur when all of the following conditions are met:
- `publisher` is not `None`
- `trigger()` returns `PluginRunStatus.SUCCEEDED`
- `request.capability` equals `"source.fetch"`
- `invocation.result` is not `None`
- `invocation.result.output` is not `None`

#### Scenario: non-source.fetch capability does not publish
- **GIVEN** a `PluginSchedulingService` with a publisher
- **WHEN** `trigger()` is called with capability `"notification.send"`
- **AND** the plugin execution succeeds
- **THEN** no event SHALL be published

#### Scenario: failed execution does not publish source event
- **GIVEN** a `PluginSchedulingService` with a publisher
- **WHEN** `trigger()` returns `FAILED` or `TIMEOUT`
- **THEN** no `source.event.captured` event SHALL be published

### Requirement: Publishing delegates to SourceEventPublisher

The scheduling service SHALL NOT construct `EventEnvelope` directly. It SHALL delegate to the existing `SourceEventPublisher.publish_source_fetch_result()` method, converting `invocation.result.output` to `SourceFetchResult` via `SourceFetchResult.from_mapping()`.

#### Scenario: output is converted to SourceFetchResult before publishing
- **GIVEN** a successful `source.fetch` invocation with output `{"items": [...], ...}`
- **WHEN** the scheduling service publishes the result
- **THEN** it SHALL call `SourceFetchResult.from_mapping(invocation.result.output, stage="publish")`
- **AND** pass the result to `SourceEventPublisher.publish_source_fetch_result()` with `producer="plugin-scheduling"`, `request_id` from the trigger request, `plugin_id` from the trigger request, and `causation_id` set to `run.run_id`

### Requirement: Publishing failure does not affect scheduling record

If the event publishing fails for any reason (conversion error, publisher error, etc.), the failure SHALL NOT change the `PluginRunRecord.status`. The scheduling service SHALL log a warning and return the `SUCCEEDED` record unchanged.

#### Scenario: publish conversion fails
- **GIVEN** a successful `source.fetch` invocation with malformed output
- **WHEN** `SourceFetchResult.from_mapping()` raises an exception
- **THEN** the `PluginRunRecord` SHALL still have status `SUCCEEDED`
- **AND** a warning SHALL be logged containing `plugin_id`, `run_id`, and `error_type`

#### Scenario: publisher raises an exception
- **GIVEN** a successful `source.fetch` invocation and a publisher that raises
- **WHEN** `publisher.publish()` raises an exception
- **THEN** the `PluginRunRecord` SHALL still have status `SUCCEEDED`
- **AND** a warning SHALL be logged containing `plugin_id`, `run_id`, and `error_type`

### Requirement: Zero regression guarantee

All existing tests in `packages/core/tests/test_scheduling.py` SHALL pass without modification after the change is implemented.

#### Scenario: existing tests pass unchanged
- **GIVEN** the existing test suite for `PluginSchedulingService`
- **WHEN** the optional publisher feature is added
- **THEN** all existing tests SHALL pass without any test code modification

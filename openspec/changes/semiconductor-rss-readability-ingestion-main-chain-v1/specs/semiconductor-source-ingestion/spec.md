## ADDED Requirements

### Requirement: Semiconductor industry package MUST declare RSS as required source and Readability as optional enrichment source

The system SHALL define the first semiconductor / memory industry ingestion chain through industry-owned `source_bindings`, where RSS is the required discovery source and Readability is the optional article-content enrichment source.

#### Scenario: Industry package declares stable source dependencies
- **WHEN** the official semiconductor / memory industry package is defined
- **THEN** it MUST declare at least one required RSS source binding
- **AND** it MUST declare Readability as an optional source dependency for content enrichment
- **AND** those dependencies MUST be expressed through `source_bindings` templates instead of hardcoded HTTP calls inside the industry package

#### Scenario: Required and optional dependencies stay separated
- **WHEN** source binding templates are prepared for the semiconductor package
- **THEN** high-stability public feeds MUST be represented as required or default-enabled bindings
- **AND** broader or noisier news / analyst sources MAY be represented as optional bindings
- **AND** the package MUST NOT treat optional enrichment failure as equivalent to required RSS discovery failure

### Requirement: First-wave semiconductor RSS templates MUST separate stable feeds from optional expansion feeds

The system SHALL provide a first-wave semiconductor RSS template set that distinguishes stable baseline feeds from optional expansion feeds.

#### Scenario: Stable feeds are available as baseline templates
- **WHEN** the semiconductor package ships default source-binding templates
- **THEN** the baseline set MUST cover high-stability public sources such as official company newsrooms, high-stability industry news sources, or equivalent AI-relevant public feeds
- **AND** those baseline feeds MUST be suitable for default enablement in V1

#### Scenario: Expansion feeds remain optional in V1
- **WHEN** broader industry commentary, analyst commentary, or noisier aggregation sources are included
- **THEN** they MUST be modeled as optional or separately enabled templates
- **AND** V1 MUST NOT require them for the package to function
- **AND** their inclusion MUST NOT redefine the baseline feed set as all-on by default

### Requirement: Scheduler MUST publish RSS captures before article enrichment

The system SHALL preserve RSS capture as the first platform fact and SHALL NOT make Readability enrichment a scheduler-side precondition for capture publication.

#### Scenario: Scheduler publishes source capture after RSS fetch
- **WHEN** scheduler triggers an RSS source binding and the fetch succeeds
- **THEN** scheduler MUST publish `source.event.captured`
- **AND** the published event MUST represent RSS capture output before Readability enrichment
- **AND** scheduler MUST NOT synchronously require article-body enrichment to complete before publishing the captured event

#### Scenario: RSS capture remains valid without enrichment
- **WHEN** RSS fetch produces title, URL, summary, author, or published time but no enriched article body yet
- **THEN** the platform MUST still treat the capture as a valid source discovery result
- **AND** downstream enrichment MAY happen later in worker-owned processing

### Requirement: Worker MUST perform article enrichment through a controlled seam after `source.event.captured`

The system SHALL perform Readability-based article enrichment after worker receives `source.event.captured`, using a controlled platform seam instead of embedding enrichment logic inside the RSS plugin.

#### Scenario: Worker decides whether a captured item needs article enrichment
- **WHEN** worker consumes a captured source event for a semiconductor industry binding
- **THEN** worker MUST determine whether each captured item requires article-body enrichment
- **AND** that decision MUST happen through worker-side or core-side orchestration logic
- **AND** the RSS source plugin MUST NOT directly invoke Readability on its own

#### Scenario: Enrichment uses a controlled Readability seam
- **WHEN** a captured item requires article enrichment
- **THEN** worker MUST invoke a controlled enrichment seam backed by Readability or an equivalent platform-owned interface
- **AND** worker MUST NOT hardcode plugin-to-plugin imports for `plugins/sources/readability-source`
- **AND** the enrichment call MUST remain replaceable by a later platform adapter or topic-driven implementation

### Requirement: Enrichment failure MUST degrade to RSS-summary consumption with explicit failure marking

The system SHALL keep the semiconductor ingestion chain running when Readability enrichment fails, while marking the degraded input explicitly.

#### Scenario: Readability failure does not block downstream routing
- **WHEN** article enrichment fails for a captured RSS item
- **THEN** the platform MUST continue with the RSS-derived title / URL / summary form when that capture is still analyzable
- **AND** the platform MUST attach structured metadata indicating enrichment failure or incomplete article content
- **AND** the failure MUST NOT be silently swallowed

#### Scenario: Downstream consumers can distinguish degraded inputs
- **WHEN** an enriched or degraded item is routed toward industry analysis
- **THEN** downstream consumers MUST be able to distinguish whether full article enrichment succeeded
- **AND** degraded inputs MUST NOT be represented as if complete article text had been obtained

### Requirement: Worker MUST publish `industry.analysis.requested` for the semiconductor owner after enrichment routing

The system SHALL express the handoff from source ingestion to industry analysis through the `industry.analysis.requested` topic for the semiconductor owner.

#### Scenario: Successful enrichment or degradation produces an industry-analysis request
- **WHEN** worker finishes routing a semiconductor-owned captured source item
- **AND** the item is eligible for downstream analysis
- **THEN** worker MUST publish `industry.analysis.requested`
- **AND** the published request MUST identify the semiconductor industry owner derived from `binding_id`
- **AND** the request MUST preserve message identity or correlation context linking back to the captured source event

#### Scenario: Worker does not directly invoke semiconductor analysis implementation in V1
- **WHEN** worker hands off a semiconductor source item toward industry analysis
- **THEN** it MUST do so through `industry.analysis.requested`
- **AND** worker MUST NOT directly hardcode semiconductor plugin imports or `if/else` owner dispatch as the final analysis execution path

### Requirement: `industry.analysis.requested` adoption MUST update stable event-bus contracts

The system SHALL treat the semiconductor ingestion handoff as an event-bus contract change, not as an ad hoc local topic.

#### Scenario: Topic policy is updated together with the new handoff
- **WHEN** the semiconductor ingestion main chain adopts `industry.analysis.requested` as the analysis handoff
- **THEN** the stable event topic policy MUST allow `industry.analysis.requested`
- **AND** the corresponding Event Bus contract documentation and tests MUST be updated
- **AND** the topic MUST NOT be introduced only in implementation code

#### Scenario: Published requests remain structured and auditable
- **WHEN** worker publishes `industry.analysis.requested`
- **THEN** the payload MUST be JSON-safe and auditable
- **AND** it MUST preserve the owner identity, source trace context, and degraded/enriched status needed by downstream analysis
- **AND** it MUST NOT contain ORM objects, plugin instances, or secret-bearing runtime objects

### Requirement: RawEvent persistence MUST preserve RSS capture fact before enrichment-dependent analysis handoff

The system SHALL preserve the RSS capture fact before enrichment-driven routing changes the downstream analysis input.

#### Scenario: RSS fact enters platform truth before enrichment-dependent analysis
- **WHEN** the platform persists or normalizes scheduler-owned RSS captures
- **THEN** the initial persisted fact MUST represent RSS discovery output before article enrichment is required
- **AND** enrichment MUST NOT become a precondition for the existence of the source-capture fact

#### Scenario: Later analysis input may incorporate enrichment outcome
- **WHEN** article enrichment succeeds after the initial RSS capture fact exists
- **THEN** downstream analysis input MAY include enriched article content
- **AND** the platform MUST still preserve traceability back to the earlier RSS capture fact
- **AND** V1 MUST NOT require full dual-layer persistence of enriched article state to accept the ingestion chain

### Requirement: V1 semiconductor ingestion acceptance MUST cover the end-to-end handoff from RSS capture to analysis-request topic

The system SHALL verify the first semiconductor ingestion chain as a minimal end-to-end flow from source binding trigger through analysis-request publication.

#### Scenario: Required V1 harness proves the main chain
- **WHEN** the implementation PR claims the semiconductor ingestion chain is complete
- **THEN** the verification MUST cover:
  - required semiconductor RSS templates producing valid source bindings
  - scheduler triggering RSS fetch for a semiconductor binding
  - `source.event.captured` being published
  - worker resolving `binding_id -> owner=industry:semiconductor`
  - worker attempting Readability enrichment through the controlled seam when needed
  - degraded continuation when enrichment fails
  - publication of `industry.analysis.requested` with structured owner and trace context

#### Scenario: External-feed instability is not required for V1 acceptance
- **WHEN** V1 verification is executed
- **THEN** fixture-based or otherwise controlled inputs MAY be used
- **AND** live external RSS or live article websites MUST NOT be required for acceptance

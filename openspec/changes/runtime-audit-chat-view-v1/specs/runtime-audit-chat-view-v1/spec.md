## ADDED Requirements

### Requirement: Runtime audit page MUST use real RawEvent-backed news items as the primary unit

`/runtime` SHALL present one news item / RawEvent as the primary audit unit and SHALL NOT use frontend fixture event-topic messages as production data.

#### Scenario: Runtime left list is news-based
- **WHEN** a user opens `/runtime`
- **THEN** the left list MUST render news items derived from real RawEvent backend data
- **AND** each list item MUST use the news title as the main label
- **AND** the list MUST NOT use `industry.analysis.requested` or `event.routed` as the primary row title

#### Scenario: Frontend fixture is not production data source
- **WHEN** Runtime audit data is loaded in the normal app
- **THEN** the frontend MUST request the backend read model
- **AND** it MUST NOT call local fixture constructors as the production query result
- **AND** fixture data MAY remain only as test or harness input

### Requirement: Backend MUST expose a sanitized Runtime audit news read model

The API SHALL expose a read-only `GET /api/v1/runtime/audit/news` endpoint backed by persisted RawEvent facts.

#### Scenario: News audit endpoint returns list-safe data
- **WHEN** an authorized user requests `GET /api/v1/runtime/audit/news`
- **THEN** the API MUST return RawEvent-backed news audit items
- **AND** each item MUST include title, URL summary, source plugin, capture timestamps, trace summary, current stage, focus stage and timeline summary
- **AND** the response MUST NOT include full article `content` or `raw_payload`

#### Scenario: Endpoint keeps runtime inspect permission
- **WHEN** a caller lacks `runtime.inspect`
- **THEN** the endpoint MUST return the existing protected-route permission behavior
- **AND** it MUST NOT leak RawEvent metadata through an unauthenticated or unauthorized response

### Requirement: Runtime audit news timeline MUST represent persisted Router Agent output honestly

The system SHALL show persisted Router Agent output when a safe read model exists and SHALL keep AI intake and route stages unavailable or pending when no persisted route-decision read model exists.

#### Scenario: Route decision is shown from persisted output
- **WHEN** a RawEvent has a persisted Router Agent routed-event read model
- **THEN** its timeline MUST include AI intake / route decision steps derived from that persisted fact
- **AND** the page MUST show the persisted `route`, `review` or `discard` decision
- **AND** the displayed decision MUST preserve traceability to the RawEvent and `event.routed` message

#### Scenario: Route decision is not mocked
- **WHEN** a RawEvent has no persisted AI intake or routed-event fact available to the Runtime audit read model
- **THEN** its timeline MUST include an unavailable or pending AI/route step
- **AND** the page MUST NOT display fabricated `route`, `review` or `discard` decisions
- **AND** the unavailable step MUST explain that the persisted read model is not available in V1

#### Scenario: Captured facts remain visible despite unavailable route stage
- **WHEN** RawEvent capture data exists but AI routing data is unavailable
- **THEN** the page MUST still show the news item, capture facts and scheduler/binding refs
- **AND** it MUST mark only the missing AI/route stage as unavailable

### Requirement: Worker MUST persist Router Agent routed output as a safe runtime audit read model

The worker SHALL persist the structured Router Agent outcome after publishing `event.routed`, so Runtime audit can show real AI processing output without reading fixture data or provider raw responses.

#### Scenario: Routed event is persisted after publish
- **WHEN** worker handles an `industry.analysis.requested` item and publishes `event.routed`
- **THEN** worker MUST persist a safe routed-event read model
- **AND** the persisted record MUST include `event_id`, `raw_event_id` when available, owner, binding, request/correlation context, decision, summary, key fields and structured output JSON
- **AND** persistence MUST be idempotent by routed event id

#### Scenario: Persisted output stays safe
- **WHEN** Router Agent output is persisted for runtime audit
- **THEN** the stored `output_json` MUST be JSON-safe structured output
- **AND** it MUST NOT include provider raw response, chain-of-thought, secret values, ORM objects, plugin instances or unbounded article content

#### Scenario: Scheduler trace enables RawEvent linkage
- **WHEN** scheduler persists RawEvent facts before publishing `source.event.captured`
- **THEN** the published source item metadata SHOULD include RawEvent trace identifiers such as `raw_event_id`, capture id, binding id, scheduler run id and request id
- **AND** worker MAY use those metadata fields to link Router Agent output back to the selected news item

### Requirement: Runtime audit details MUST be organized around selected news

The right-side detail area SHALL summarize the selected news item instead of showing per-topic event details.

#### Scenario: Selected news detail is structured
- **WHEN** a user selects a news item
- **THEN** the detail area MUST show news summary, current progress, timeline, trace refs and safe details
- **AND** it MUST keep full article body retrieval out of the default runtime audit list/detail response

#### Scenario: Details remain safe
- **WHEN** safe details are rendered
- **THEN** they MUST be allowlisted metadata summaries
- **AND** they MUST NOT include raw prompt, full chain-of-thought, provider raw response, secret values, ORM objects, plugin instances, connection strings, full article content or raw payload

### Requirement: Runtime audit details MUST expose auditable Agent stages when persisted output exists

`/runtime` SHALL make the selected news processing flow inspectable by Agent stage, especially Router Agent output, while remaining honest when output has no persisted read model.

#### Scenario: Router Agent output is shown when available
- **WHEN** the backend read model contains a persisted Router Agent structured output for the selected RawEvent
- **THEN** the detail area MUST show a Router Agent stage
- **AND** it MUST render important fields such as decision, summary, relevance, routing targets, quality and review/deep-analysis flags as UI fields
- **AND** it MUST provide the complete structured output JSON
- **AND** it MUST NOT show provider raw response, chain-of-thought, secrets or unbounded article content

#### Scenario: Missing Agent output is not fabricated
- **WHEN** no persisted Router Agent or MainAgent output is available
- **THEN** the detail area MUST still show the Agent stage as unavailable or pending
- **AND** it MUST include an explicit unavailable reason
- **AND** it MUST NOT fabricate `route`, `review`, `discard`, summary or routing targets from fixture data in production

#### Scenario: Future industry MainAgent stages can be added without changing the list unit
- **WHEN** industry MainAgent analysis output is later persisted
- **THEN** it MAY be added as another Agent stage for the selected news
- **AND** the left list MUST remain one news item / RawEvent per row
- **AND** timeline and Agent stages MUST preserve traceability back to the RawEvent

### Requirement: Runtime audit filters MUST query the news read model

Runtime audit filters SHALL apply to the backend news read model rather than only filtering local fixtures.

#### Scenario: News filters are supported
- **WHEN** a user filters Runtime audit news
- **THEN** the query MUST support keyword/title, binding id, source plugin id, status/current stage, time range, trace id and request id where backend data exists
- **AND** filters MUST be encoded in query params sent to the backend endpoint
- **AND** invalid or empty filter values MUST NOT crash the page

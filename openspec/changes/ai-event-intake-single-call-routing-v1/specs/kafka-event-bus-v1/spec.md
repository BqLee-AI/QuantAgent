## ADDED Requirements

### Requirement: `event.routed` MUST 支持 AI intake routing decision payload

系统 SHALL 将 `event.routed` 作为 `industry.analysis.requested` 之后 AI intake routing decision 的 V1 稳定 Event Bus topic。

#### Scenario: AI intake 发布 routed outcome
- **WHEN** AI intake 校验出一个 `decision=route` 的 `EventIntakeDecisionV1`
- **THEN** 它 MUST 发布一个 `event.routed` envelope
- **AND** payload MUST 标识自身 schema 为 AI intake routing decision，例如 `event_intake_decision.v1`
- **AND** payload MUST 保留 trace context，使其可追溯到 `industry.analysis.requested` message 和可用的 upstream source capture
- **AND** payload MUST 包含 target industry identifiers 和 structured routing metadata

#### Scenario: AI intake 发布 discard 或 review outcome
- **WHEN** AI intake 校验出一个 `decision=discard` 或 `decision=review` 的 `EventIntakeDecisionV1`
- **THEN** 它 MUST 通过 `event.routed` 发布该 outcome
- **AND** discard outcomes MUST 包含 structured discard reason 和 trace context
- **AND** review outcomes MUST 包含 uncertainty 或 review reason 以及 trace context
- **AND** downstream deep-analysis consumers MUST 能够不解析自然语言就区分 discard、route 和 review outcomes

#### Scenario: Event routed payload 保持 JSON-safe
- **WHEN** AI intake outcome 发布到 `event.routed`
- **THEN** payload 和 headers MUST 是 JSON-safe
- **AND** 它们 MUST NOT 包含 ORM objects、plugin instances、provider clients、secret-bearing runtime objects、完整 provider raw responses 或完整 chain-of-thought
- **AND** envelope MUST 保留适合 audit 和 replay 的 correlation 与 causation identifiers

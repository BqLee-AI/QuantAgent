# API Client Error Governance Specification

## MODIFIED Requirements

### Requirement: Error Governance

前端 SHALL 统一封装 API 失败语义，并为 capability guard 与 403 权限不足 UX 提供稳定的错误元数据。

#### Scenario: ApiError preserves metadata

- **WHEN** 抛出 `ApiError`
- **THEN** 至少包含 `code`、`msg`、`status`
- **AND** 如可用则包含 `requestId` 和 `traceId`

#### Scenario: Error registry maps business codes to UI behavior

- **WHEN** 查询 `ErrorRegistry`
- **THEN** 可获得 `toast | modal | silent | redirect` 等默认 UI 行为
- **AND** registry 本身不直接渲染 UI

#### Scenario: Global error hook can observe failures

- **WHEN** client 产生 `ApiError`
- **THEN** 若配置了 `onError`，该 hook 会收到统一错误对象

#### Scenario: Forbidden error remains distinguishable from generic network failures

- **WHEN** shared API client 收到 403 响应
- **THEN** 前端错误对象保留权限不足语义与元数据
- **AND** capability guard 或页面 UI 可以基于该对象渲染统一 forbidden 体验
- **AND** 403 不会被伪装成普通网络错误

#### Scenario: Forbidden diagnostics stay available without leaking secrets

- **WHEN** 403 响应附带 `request_id` 或 `trace_id`
- **THEN** shared API client SHALL 把这些字段保留到 `ApiError`
- **AND** 前端错误对象、共享状态和日志中仍不暴露 session cookie、cookie value、password、password hash、signing secret、真实 token 或私有策略原文

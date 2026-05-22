## Why

QuantAgent 已经在设计文档中确定 Source Plugin 是事件进入系统的第一段边界，但当前代码只有 placeholder source，缺少真实 pull source 到 RawEvent 的可验证闭环。现在先收住 RSS Source 到 RawEvent 入库，可以避免后续行业包、Router Agent 和前端事件页继续依赖临时 mock，也避免把采集逻辑误塞进 API 层或具体插件自调度循环。

## What Changes

- 定义最小 pull Source Plugin 协议，覆盖 `load`、`start`、`stop`、`reload`、`health_check` 和 `fetch`。
- 定义 `RawEventDraft` / `StoredRawEvent` DTO，并实现 RawEvent 去重 identity。
- 增加 RawEvent、SourceBinding、SourceFetchRun 的 ORM model 和 Alembic migration。
- 增加 RawEvent repository，封装去重入库。
- 增加 SourceFetchService，用于手动触发 SourceBinding fetch，并记录抓取数、入库数、重复数、耗时和错误摘要。
- 增加最小插件 manifest 发现/解析能力，用于识别 source 插件。
- 新增官方 RSS Source Plugin，支持 RSS / Atom feed 解析并产出 RawEventDraft。
- 保持 Source Plugin 采集边界：不做行业判断，不启动轮询循环，不接入 Playwright/代理池/复杂反爬。

## Capabilities

### New Capabilities

- `source-rss-ingestion`: RSS pull source 通过 SourceBinding 手动触发，产出 RawEvent，并以可去重、可记录 fetch run 的方式持久化。

### Modified Capabilities

无。

## Impact

- `packages/core/src/quantagent/core/events/`
- `packages/core/src/quantagent/core/sources/`
- `packages/core/src/quantagent/core/plugins/`
- `packages/core/src/quantagent/core/db/`
- `packages/core/alembic/versions/`
- `packages/core/tests/test_core.py`
- `plugins/sources/rss-source/`
- 数据库新增 `raw_events`、`source_bindings`、`source_fetch_runs` 表。
- 不新增 Python 第三方依赖；RSS/Atom 解析使用标准库。

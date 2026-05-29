# API services

本目录存放 API 私有 service / usecase 边界，用于承接不适合塞进 FastAPI router 的传输层编排。

- 可以放：请求配置组装、调用 core package、把插件或 package 结果映射成 HTTP 层结果。
- 不放：可跨 worker / scheduler / plugin 复用的核心领域逻辑、数据库基础设施、插件生命周期托管、API DTO schema。
- 如果能力开始被其他 app 或 package 复用，应先通过 issue / OpenSpec 明确边界，再下沉到对应 `packages/*`。

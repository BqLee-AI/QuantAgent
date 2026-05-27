## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `enable-real-discord-interaction-webhook` change 的 proposal、design、specs、tasks 和必要元数据。
- [ ] 1.2 在 PR 说明中写清楚：本 change 的目标是让 Discord interaction webhook 能真实打到 QuantAgent，并补齐官方验签、`PING` 握手、最小响应和 plugin entrypoint 调用边界。
- [ ] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. API ingress 与配置

- [ ] 2.1 在 `apps/api` 中新增 Discord interaction webhook 的公开 `POST` 路由，并通过 `register_api_v1_routes` 注册。
- [ ] 2.2 为该路由补充最小 API 配置：endpoint 开关、目标 plugin id、Discord public key 值或引用。
- [ ] 2.3 确保路由读取原始 body 和 Discord 签名头，并把失败结果映射为稳定 HTTP 响应。

## 3. Plugin loader 与 source plugin 升级

- [ ] 3.1 在 `packages/core` 或等价共享位置补充最小 plugin entrypoint loader，允许根据 Registry record 加载 source plugin 对象。
- [ ] 3.2 将 `plugins/sources/discord-interaction-webhook` 从 HMAC fixture 生产逻辑升级为 Discord 官方 `Ed25519` 验签逻辑。
- [ ] 3.3 让 source plugin 支持 `PING` 和最小 `APPLICATION_COMMAND` 解析，并返回可映射为 Discord interaction response 的结构化结果。
- [ ] 3.4 确保插件和路由错误结果不暴露公钥原文、内部路径、traceback 或完整原始 payload。

## 4. 测试与文档

- [ ] 4.1 为 API 路由补充测试，覆盖签名失败、`PING` 成功、合法 command 成功和不支持 interaction type。
- [ ] 4.2 为 source plugin 补充或重写测试，覆盖官方签名校验、DTO 解析和最小 interaction response 结果。
- [ ] 4.3 为 plugin loader 补充测试，覆盖合法 manifest entrypoint 加载和非法配置失败。
- [ ] 4.4 更新 `plugins/sources/discord-interaction-webhook/README.md` 与 `apps/api/README.md`，说明真实接收配置和 smoke test 步骤。

## 5. 真实验证与收口

- [ ] 5.1 运行与改动范围匹配的 Python 测试，并在实现 PR 中记录实际执行命令和结果。
- [ ] 5.2 在本地或测试环境暴露可访问的 HTTPS endpoint，完成 Discord Developer Portal 的 `PING` 验证。
- [ ] 5.3 使用真实 Discord interaction 做一次最小 smoke test，并在实现 PR 中明确这是“补充验证”还是“默认验收项”。

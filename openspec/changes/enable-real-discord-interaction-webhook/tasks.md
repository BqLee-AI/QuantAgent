## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `enable-real-discord-interaction-webhook` change 的 proposal、design、specs、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中写清楚：本 change 的目标是让 Discord interaction webhook 能真实打到 QuantAgent，并补齐官方验签、`PING` 握手、最小响应和 plugin entrypoint 调用边界。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。
- [x] 1.4 根据会议收敛结果，把 ingress 目标从独立 source 插件改写为单个官方 Discord 插件。

## 2. API ingress 与配置

- [x] 2.1 保留 `apps/api` 中的 Discord interaction webhook 公开 `POST` 路由，并继续通过 `register_api_v1_routes` 注册。
- [x] 2.2 更新最小 API 配置：默认 Discord plugin id 指向单插件官方 plugin id。
- [x] 2.3 确保路由读取原始 body 和 Discord 签名头，并把失败结果映射为稳定 HTTP 响应。

## 3. Plugin loader 与单插件接收能力

- [x] 3.1 继续复用最小 plugin entrypoint loader，根据 Registry record 加载单个 Discord 插件对象。
- [x] 3.2 移除“必须是 source plugin”这一旧限制，改为校验 capability 与 `receive_request` handler。
- [x] 3.3 确保 Discord 插件继续支持 `PING` 和最小 `APPLICATION_COMMAND` 解析，并返回可映射为 Discord interaction response 的结构化结果。
- [x] 3.4 确保插件和路由错误结果不暴露公钥原文、内部路径、traceback 或完整原始 payload。

## 4. 测试与文档

- [x] 4.1 更新 API 路由测试，覆盖单插件配置、签名失败、`PING` 成功、合法 command 成功和不支持 interaction type。
- [x] 4.2 更新插件测试与 README，覆盖单插件下的官方签名校验、DTO 解析和最小 interaction response 结果。
- [x] 4.3 更新默认配置和运行说明，说明真实接收配置和 smoke test 步骤。

## 5. 真实验证与收口

- [x] 5.1 运行与改动范围匹配的 Python 测试，并在实现 PR 中记录实际执行命令和结果。
- [ ] 5.2 在本地或测试环境暴露可访问的 HTTPS endpoint，完成 Discord Developer Portal 的 `PING` 验证。
- [ ] 5.3 使用真实 Discord interaction 做一次最小 smoke test，并在实现 PR 中明确这是“补充验证”还是“默认验收项”。

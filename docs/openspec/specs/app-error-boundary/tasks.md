# Tasks: App Error Boundary

## 1. Error Model

- [ ] 定义统一错误展示所需的最小数据结构。
- [ ] 约束可展示字段，仅保留错误摘要与可选 `request_id` / `trace_id`。

## 2. Root Error Boundary

- [ ] 调整或补充根级 Error Boundary，确保子树渲染异常进入统一兜底界面。
- [ ] 保持现有应用启动流程和路由壳集成方式不变。

## 3. Startup Fallback Page

- [ ] 新建或重构启动失败兜底页组件。
- [ ] 覆盖 runtime 配置加载失败、路由壳初始化失败等 bootstrap 阶段错误。

## 4. Recovery Actions

- [ ] 添加重新加载页面入口。
- [ ] 添加返回首页或默认入口的入口。

## 5. Safety Guardrails

- [ ] 确认错误页不展示堆栈、密钥、环境变量或内部实现细节。
- [ ] 确认默认文案足够简短且不暴露敏感信息。

## 6. Verification

- [ ] 验证子树渲染异常会落到统一错误页。
- [ ] 验证启动阶段异常会落到统一兜底页。
- [ ] 验证恢复入口可用。


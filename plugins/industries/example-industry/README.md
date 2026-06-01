# Example Industry Package

这是一个官方 `industry` 样例插件，插件 ID 为 `quantagent.official.industry.example`。

它的存在目的只有一个：给后续行业包实现提供稳定的 `source_bindings` manifest/template 目录样例，避免每个行业包各自发明模板落点。

## 资产边界

这个行业包样例只负责：

- 在 `plugin.yaml` 中声明 `source_bindings` 元信息
- 在 `templates/source_bindings/` 中提供默认模板文件
- 用 README 解释 required / optional 语义，以及不要把什么写进模板

它不负责：

- effective config 合成
- `SourceBinding` / `SchedulerRun` 持久化
- scheduler loop、手动触发编排或 worker 路由
- source plugin 实现细节
- 真实行业分析、评分、Decision 或 broker 执行

换句话说，行业包只声明“默认依赖哪些 source，以及给这些 source 的模板入口是什么”，不承担调度主对象职责。

## 目录结构

```text
plugins/industries/example-industry/
  plugin.yaml
  config.schema.json
  industry_plugin.py
  README.md
  templates/
    source_bindings/
      rss.default.yaml
      readability.fallback.yaml
```

## source_bindings 说明

### required source

`quantagent.official.source.rss` 被声明为 `required: true`。

- 作用：表达这个行业包的默认信息入口依赖 RSS source
- 模板：`templates/source_bindings/rss.default.yaml`
- 语义：如果平台后续无法为这个行业包建立 RSS binding，这应被视为阻塞依赖

### optional source

`quantagent.official.source.readability` 被声明为 `required: false`。

- 作用：表达行业包对全文阅读增强能力的默认依赖
- 模板：`templates/source_bindings/readability.fallback.yaml`
- 语义：缺少它时不应让行业包主流程承担“自己调度 reader”职责，只能由平台决定是否降级

## 模板里应该放什么

- 行业包对 source 的默认 override，例如 feed、关键词、分类、抓取窗口提示
- 行业包可公开的默认值和非敏感过滤条件

## 模板里不要放什么

- secret 明文、token、私有账户、生产凭证
- `effective_config`
- `binding_id`
- `status`、`last_run_at`、`next_run_at`
- 调度计数、失败统计、审计字段
- 任何试图让行业包自己承担 scheduler / worker 职责的运行态字段

## 与其他 issue 的边界

- `#148` 负责 source plugin 自身实现；本样例不定义 RSS / Readability 的运行逻辑
- `#215` 负责 template 与 effective config 的合成契约；本样例不定义合成算法
- `#216` 负责 `SourceBinding` / `SchedulerRun` 持久化；本样例不定义运行态状态字段

## 最小验证

在仓库根目录执行：

```bash
uv run python -m unittest packages/core/tests/test_registry.py
uv run python -m unittest apps/api/src/tests/test_app.py
```

这里的验证目标是确认 Registry 和 API 能稳定读取 `source_bindings` 元信息，而不是验证调度或行业分析闭环。

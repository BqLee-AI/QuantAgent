# Demo Placeholder Source

这是一个最小可运行的官方 source 插件示例，用来验证插件底座链路和给后续插件作者当参照。

它不是 RSS 插件，也不接真实外部数据。它只实现 `source.fetch`，根据 `input.query` 或配置里的 `query` 返回一条标准 source 输出。

这个插件的目标是验证：

```text
plugin.yaml -> Registry -> Runtime -> Scheduling -> PluginRunRecord
```

## 文件结构

```text
plugins/sources/placeholder-source/
  plugin.yaml
  config.schema.json
  placeholder_source.py
```

## 职责边界

这个插件只做：

```text
读取 Runtime 传入的 input/config
返回 SourceFetchResult 形状的 output
```

这个插件不做：

```text
RawEvent 入库
去重
Event Bus 发布
SourceBinding
后台循环
网络请求
真实 RSS 抓取
```

平台侧的入库、去重、SourceBinding、Event Bus 和 worker loop 应该由后端 service/repository/pipeline 承接，不能写进插件内部。

## 调用结果示例

输入：

```json
{
  "query": "rss"
}
```

输出摘要会包含：

```json
{
  "items": [
    {
      "external_id": "placeholder:rss",
      "title": "Placeholder item for rss"
    }
  ],
  "metadata": {
    "source": "placeholder"
  }
}
```

## 本地验证

从仓库根目录运行完整插件底座相关测试：

```bash
PYTHONPATH=packages/core/src:packages/plugin-sdk/src python -m unittest packages.core.tests.test_plugin_foundation_demo packages.core.tests.test_scheduling packages.core.tests.test_runtime packages.core.tests.test_registry
```

只运行这个 demo 的冒烟用例：

```bash
PYTHONPATH=packages/core/src:packages/plugin-sdk/src python -m unittest packages.core.tests.test_plugin_foundation_demo
```

这个命令会打印中文阶段日志，展示 Registry、Runtime、Scheduling 分别验证了什么能力，以及哪些能力仍不属于这个 demo。

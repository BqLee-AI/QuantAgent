# Plugin Registry V1 伪代码使用示例

本文用接近自然语言的伪代码说明 Plugin Registry V1 怎么被使用。它不是 Python 教程，也不是完整插件运行时设计；目标是帮助 reviewer、维护者和后续插件作者理解 V1 已经做到哪一步，以及哪些能力仍然刻意没有实现。

## 1. 准备插件目录

官方插件放在 `plugins/`，运行时插件放在 `runtime/plugins/`。

```text
plugins/
  sources/
    rss-source/
      plugin.yaml
      config.schema.json
```

`plugin.yaml` 是 V1 的插件登记真源：

```yaml
id: quantagent.official.source.rss
name: RSS Source
type: source
version: 0.1.0
entrypoint: rss_source:plugin
capabilities:
  - source.fetch
config_schema: config.schema.json
```

`config.schema.json` 描述插件配置长什么样：

```json
{
  "type": "object",
  "properties": {
    "feed_url": {
      "type": "string"
    }
  },
  "required": ["feed_url"]
}
```

## 2. 查询插件列表

管理台或调用方请求：

```text
GET /api/v1/plugins
```

V1 内部流程：

```text
API 收到请求
  -> 获取 PluginRegistry
  -> 如果还没有扫描过
      -> 调用 RegistryScanner.scan()
      -> 扫描 plugins/
      -> 扫描 runtime/plugins/
      -> 找到所有 plugin.yaml
      -> 读取 YAML
      -> 校验必填字段
      -> 校验 type 是否在 V1 支持集合
      -> 校验 config.schema.json 是否存在且位于插件目录内
      -> 生成 PluginRecord
  -> API 把 PluginRecord 转成 PluginRecordResponse
  -> 返回 ApiResponse envelope
```

合法插件返回示例：

```json
{
  "code": 0,
  "msg": "ok",
  "error": null,
  "data": [
    {
      "id": "quantagent.official.source.rss",
      "source": "official",
      "status": "valid",
      "path": "plugins/sources/rss-source",
      "manifest": {
        "id": "quantagent.official.source.rss",
        "name": "RSS Source",
        "type": "source",
        "version": "0.1.0",
        "entrypoint": "rss_source:plugin",
        "capabilities": ["source.fetch"],
        "config_schema": "config.schema.json",
        "description": null,
        "permissions": [],
        "dependencies": {}
      },
      "last_error": null
    }
  ]
}
```

## 3. 查询单个插件

调用方请求：

```text
GET /api/v1/plugins/quantagent.official.source.rss
```

V1 内部流程：

```text
API 收到 plugin_id
  -> PluginRegistry.get_plugin(plugin_id)
  -> 找到则返回该 PluginRecord
  -> 找不到则返回 404 envelope
```

## 4. 查询配置 schema

调用方请求：

```text
GET /api/v1/plugins/quantagent.official.source.rss/config-schema
```

V1 内部流程：

```text
API 收到 plugin_id
  -> 找到插件记录
  -> 确认插件有可用 config_schema_path
  -> 读取 config.schema.json
  -> 返回 JSON Schema
```

返回示例：

```json
{
  "code": 0,
  "msg": "ok",
  "error": null,
  "data": {
    "type": "object",
    "properties": {
      "feed_url": {
        "type": "string"
      }
    },
    "required": ["feed_url"]
  }
}
```

如果插件存在但 manifest 或 schema 非法，返回 400 envelope，而不是假装插件不存在：

```json
{
  "code": 40000,
  "data": null,
  "msg": "Plugin config schema is not available",
  "error": {
    "code": "BAD_REQUEST",
    "request_id": "req_123",
    "trace_id": null,
    "details": {
      "plugin": {
        "id": "quantagent.official.source.bad",
        "status": "invalid",
        "last_error": {
          "code": "PLUGIN_CONFIG_SCHEMA_NOT_FOUND",
          "message": "Plugin config schema file does not exist.",
          "stage": "validate",
          "details": {
            "config_schema": "missing.json"
          },
          "retryable": false
        }
      }
    },
    "retryable": false
  }
}
```

## 5. 重新扫描插件

调用方请求：

```text
POST /api/v1/plugins/actions/rescan
X-CSRF-Token: <csrf_token>
```

V1 内部流程：

```text
API 校验登录态
  -> API 校验 CSRF
  -> PluginRegistry.rescan()
  -> RegistryScanner 重新扫描 plugins/ 和 runtime/plugins/
  -> 返回扫描摘要和最新插件列表
```

返回示例：

```json
{
  "code": 0,
  "msg": "ok",
  "error": null,
  "data": {
    "summary": {
      "total": 2,
      "valid": 1,
      "invalid": 1,
      "failed": 0,
      "sources": {
        "official": 2
      }
    },
    "plugins": []
  }
}
```

## 6. 坏插件不会拖垮整体扫描

如果某个插件写成：

```yaml
id: quantagent.official.source.bad
name: Bad Plugin
type: unknown_type
version: 0.1.0
entrypoint: bad:plugin
capabilities:
  - source.fetch
config_schema: config.schema.json
```

V1 不会让 `GET /api/v1/plugins` 整体 500，而是只把这个插件标记为 `invalid`：

```json
{
  "id": "quantagent.official.source.bad",
  "source": "official",
  "status": "invalid",
  "manifest": null,
  "last_error": {
    "code": "PLUGIN_TYPE_UNKNOWN",
    "message": "Plugin type is not supported by Registry V1.",
    "stage": "validate",
    "details": {
      "type": "unknown_type",
      "supported_types": [
        "source",
        "industry",
        "strategy",
        "notification",
        "trade_executor"
      ]
    },
    "retryable": false
  }
}
```

## 7. V1 明确不做什么

V1 只做：

```text
发现 plugin.yaml
校验 manifest
校验 config.schema.json
返回 PluginRecord
暴露查询和 rescan API
```

V1 不做：

```text
import entrypoint
实例化插件
启动插件
安装插件依赖
热重载插件代码
注册 ToolRegistry
创建 SourceBinding
执行真实交易
```

后续插件系统应在 V1 之上继续分阶段推进：

```text
V1 Registry + API 查询
  -> V1.1 最小 source demo
  -> V1.2 配置保存与 schema-driven 表单
  -> V1.3 RuntimeContext + health_check
  -> V1.4 SourceBinding + Scheduler + RawEvent
  -> 后续 ToolRegistry / Policy Gate / Audit / dry-run executor
```

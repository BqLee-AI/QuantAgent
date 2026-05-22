# Plugin Registry V1 伪代码使用示例

本文用接近自然语言的伪代码说明 Plugin Registry V1 的使用方式，帮助 reviewer、维护者和后续插件作者理解 V1 的能力边界。

所有 `/api/v1/plugins*` 接口都挂在 protected router 下，调用前需要先登录并携带 session cookie；`POST /api/v1/plugins/actions/rescan` 还需要携带 `X-CSRF-Token`。

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

`config.schema.json` 描述插件配置形态：

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

```text
GET /api/v1/plugins
Cookie: quantagent_session=...
```

V1 内部流程：

```text
校验登录态
  -> 获取 PluginRegistry
  -> 如果还没有扫描过，调用 RegistryScanner.scan()
  -> 扫描 plugins/ 和 runtime/plugins/
  -> 找到所有 plugin.yaml
  -> 读取 YAML
  -> 校验必填字段、type、capabilities 和 config.schema.json
  -> 生成 PluginRecord
  -> API 把 PluginRecord 转成 PluginRecordResponse
  -> 返回 ApiResponse envelope
```

返回关键字段示意：

```json
{
  "code": 0,
  "data": [
    {
      "id": "quantagent.official.source.rss",
      "source": "official",
      "status": "valid",
      "manifest": {
        "type": "source",
        "capabilities": ["source.fetch"]
      },
      "last_error": null
    }
  ],
  "error": null
}
```

## 3. 查询单个插件

```text
GET /api/v1/plugins/quantagent.official.source.rss
Cookie: quantagent_session=...
```

V1 内部流程：

```text
校验登录态
  -> API 收到 plugin_id
  -> PluginRegistry.get_plugin(plugin_id)
  -> 找到则返回该 PluginRecord
  -> 找不到则返回 404 envelope
```

## 4. 查询配置 schema

```text
GET /api/v1/plugins/quantagent.official.source.rss/config-schema
Cookie: quantagent_session=...
```

V1 内部流程：

```text
校验登录态
  -> 找到插件记录
  -> 确认插件有可用 config_schema_path
  -> 读取 config.schema.json
  -> 返回 JSON Schema
```

成功返回关键字段示意：

```json
{
  "code": 0,
  "data": {
    "type": "object",
    "properties": {
      "feed_url": {
        "type": "string"
      }
    },
    "required": ["feed_url"]
  },
  "error": null
}
```

如果插件存在但 manifest 或 schema 非法，返回 400 envelope，而不是假装插件不存在。`details.plugin.last_error` 当前只返回脱敏摘要字段：

```json
{
  "code": 40000,
  "data": null,
  "msg": "Plugin config schema is not available",
  "error": {
    "code": "BAD_REQUEST",
    "details": {
      "plugin": {
        "id": "quantagent.official.source.bad",
        "status": "invalid",
        "last_error": {
          "code": "PLUGIN_CONFIG_SCHEMA_NOT_FOUND",
          "stage": "validate",
          "retryable": false
        }
      }
    },
    "retryable": false
  }
}
```

## 5. 重新扫描插件

```text
POST /api/v1/plugins/actions/rescan
Cookie: quantagent_session=...
X-CSRF-Token: <csrf_token>
```

V1 内部流程：

```text
校验登录态
  -> 校验 CSRF
  -> PluginRegistry.rescan()
  -> RegistryScanner 重新扫描 plugins/ 和 runtime/plugins/
  -> 返回扫描摘要和最新插件列表
```

返回关键字段示意，`summary.total` 应与 `plugins` 列表一致：

```json
{
  "code": 0,
  "data": {
    "summary": {
      "total": 1,
      "valid": 1,
      "invalid": 0,
      "failed": 0
    },
    "plugins": [
      {
        "id": "quantagent.official.source.rss",
        "source": "official",
        "status": "valid"
      }
    ]
  },
  "error": null
}
```

## 6. 坏插件不会拖垮整体扫描

如果某个插件声明了未知 type：

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
    "stage": "validate",
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

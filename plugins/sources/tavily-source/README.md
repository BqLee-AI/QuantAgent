# Tavily Source Tool

`Tavily Source Tool` 是官方 `source` 插件，提供基于 Tavily API 的证据导向搜索和内容提取能力。

## 能力边界

- 默认提供 `source.fetch`，并兼容 `source.search` 和 `source.extract` 两种细分调用语义。
- 只消费平台传入的校验后配置 / `effective_config`。
- 返回 `plugin-sdk` 定义的 `SourceFetchResult`，保持 source 插件 DTO 契约一致。
- **不负责** `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期。
- **不负责** Tavily API key 的获取、验证或管理（由平台在 `api_key_ref` 配置中注入）。
- **不负责** 调度、重试、跨插件调用或 ToolRegistry 集成。

## 能力说明

### source.fetch

统一入口能力：

- 传入 `query` 时按搜索路径执行
- 传入 `url` 时按提取路径执行
- 输出统一为 `SourceFetchResult`

### source.search

执行搜索查询，并以 `SourceFetchResult.items` 返回结构化结果列表。

**必需参数：**
- `query` (str): 搜索查询字符串

**可选参数：**
- `max_results` (int): 返回结果数量（1-20，默认 5）
- `search_depth` (str): 搜索深度（"basic" 或 "advanced"，默认 "basic"）
- `include_raw_content` (bool): 是否包含原始内容（默认 false）
- `include_favicon` (bool): 是否包含网站图标（默认 false）
- `topic` (str): 搜索主题（可选）
- `include_domains` (list[str]): 仅包含指定域名（可选）
- `exclude_domains` (list[str]): 排除指定域名（可选）

### source.extract

提取指定 URL 的网页内容，并以单条 `SourceItemDraft` 返回。

**必需参数：**
- `url` (str): 要提取的 URL

**可选参数：**
- `extract_depth` (str): 提取深度（"basic" 或 "advanced"，默认 "basic"）
- `include_raw_content` (bool): 是否包含原始 HTML 内容（默认 false）
- `include_favicon` (bool): 是否包含网站图标（默认 false）
- `query` (str): 提取时的查询上下文（可选）

## 最小配置

```yaml
api_key_ref: "your-tavily-api-key"  # 必需，平台注入
timeout_seconds: 10                  # 可选，默认 10
default_max_results: 5              # 可选，默认 5
default_search_depth: "basic"       # 可选，默认 "basic"
include_favicon: false              # 可选，默认 false
include_raw_content: false          # 可选，默认 false
```

## 依赖策略

- **零外部依赖**：纯 Python 标准库实现，使用 `urllib` 进行 HTTP 请求。
- 避免插件和 core / API / web 的依赖边界绑死。
- 如果后续需要增强功能（如重试、缓存），允许只在本插件内部封装相关依赖；这类依赖仍属于插件实现细节。

## 测试

### 运行单元测试

```bash
# 在项目根目录执行
python -m unittest discover -s plugins/sources/tavily-source/tests -v
```

### 测试策略

- **静态 fixture**：使用预设的 JSON 响应文件，不依赖真实 Tavily API 稳定性。
- **受控假响应**：通过 `patch.object` 注入 fake HTTP 请求函数，隔离网络 I/O。
- **端到端验证**：通过 `PluginRuntimeService` 加载插件并执行完整调用流程。
- **DTO 对齐**：断言输出可被 `SourceFetchResult.from_mapping(...)` 解析。

## 错误处理

所有错误统一转换为 `PluginRuntimeError`，包含以下错误码：

- `PLUGIN_CAPABILITY_NOT_IMPLEMENTED`: 不支持的能力调用
- `PLUGIN_CONFIG_MISSING`: API key 配置缺失
- `PLUGIN_INVALID_INPUT`: 输入参数验证失败
- `PLUGIN_INTERNAL_ERROR`: 未预期的内部错误
- `TAVILY_AUTH_FAILED`: Tavily API key 无效（401）
- `TAVILY_RATE_LIMITED`: Tavily API 速率限制（429，可重试）
- `TAVILY_CLIENT_ERROR`: Tavily 客户端错误（4xx 其他）
- `TAVILY_SERVER_ERROR`: Tavily 服务端错误（5xx，可重试）
- `TAVILY_TIMEOUT`: 请求超时（可重试）
- `TAVILY_NETWORK_ERROR`: 网络连接错误（可重试）
- `TAVILY_INVALID_RESPONSE`: 响应解析失败

所有错误信息已脱敏，不泄露 API key 或原始响应体。

## 验证插件加载

```python
import asyncio

from quantagent.core.registry import RegistryScanner
from quantagent.core.runtime import PluginRuntimeService

# 扫描插件
records = RegistryScanner(
    official_root="plugins",
    runtime_root="runtime/plugins",
).scan()

# 加载 Tavily 插件
tavily_record = [r for r in records if r.id == "quantagent.official.source.tavily"][0]
plugin, error = asyncio.run(
    PluginRuntimeService().load_plugin(
        tavily_record,
        request_id="test-load",
        config={"api_key_ref": "test-key"},
        metadata={"origin": "test"},
    )
)

if error:
    raise AssertionError(f"Failed to load: {error}")
print(f"Loaded plugin: {plugin.context.plugin_id}")
```

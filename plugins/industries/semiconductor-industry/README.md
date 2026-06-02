# Semiconductor Industry Package

这是一个官方 `industry` 插件，插件 ID 为 `quantagent.official.industry.semiconductor`。

它的目标不是直接实现完整行业分析，而是先提供半导体 / 内存主链路所需的稳定 `source_bindings` 资产：

- required 的 RSS baseline feed 模板
- optional 的 RSS expansion feed 模板
- optional 的 Readability 正文增强模板

## 资产边界

这个行业包当前只负责：

- 在 `plugin.yaml` 中声明 `source_bindings` 元信息
- 在 `templates/source_bindings/` 中提供默认模板文件
- 用 README 解释 required / optional 语义，以及模板里不要放什么

它不负责：

- effective config 合成
- `SourceBinding` / `SchedulerRun` 持久化
- scheduler loop、worker enrichment 编排或 Event Bus publish
- 真实行业分析、评分、Decision、Approval 或 broker 执行

## 目录结构

```text
plugins/industries/semiconductor-industry/
  plugin.yaml
  config.schema.json
  industry_plugin.py
  README.md
  templates/
    source_bindings/
      rss.baseline.yaml
      rss.expansion.yaml
      readability.default.yaml
```

## source_bindings 说明

### required RSS baseline

`quantagent.official.source.rss` 的 baseline 模板表达默认启用的高稳定公开源。

- 作用：作为半导体 / 内存行业包的基础发现入口
- 模板：`templates/source_bindings/rss.baseline.yaml`
- 语义：如果平台无法建立 baseline RSS binding，则主链路不应被视为就绪

当前模板默认使用这些已复核 feed：

| Feed | 定位 | 说明 |
| --- | --- | --- |
| `https://investors.micron.com/rss/news-releases.xml` | baseline | 官方 IR feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://investor.marvell.com/news-events/press-releases/rss` | baseline | 官方 IR feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://semiengineering.com/feed/` | baseline | 半导体垂直媒体 feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://newsroom.intel.com/feed/` | baseline | 官方 newsroom feed，当前环境可访问，适合作为基础覆盖 |

### optional RSS expansion

第二个 `quantagent.official.source.rss` 模板表达扩展信息源。

- 作用：承接更广的行业新闻 / 评论类 feed
- 模板：`templates/source_bindings/rss.expansion.yaml`
- 语义：可以后续按需启用，不要求 V1 默认启用

当前模板默认使用这些扩展 feed：

| Feed | 定位 | 说明 |
| --- | --- | --- |
| `https://blogs.nvidia.com/feed/` | expansion | 官方 feed，但响应体偏大；模板已显式把 `max_response_bytes` 放宽到 `1048576` |
| `https://www.tomshardware.com/feeds/all` | expansion | 可访问的公开硬件新闻 feed，但噪音明显高于 baseline |
| `https://www.eetimes.com/feed/` | expansion | 行业媒体 feed，适合作为扩展覆盖 |
| `https://www.digitimes.com/rss/daily.xml` | expansion | 供应链与制造链信号更强，但条目量更大，适合作为 optional |
| `https://www.electronicsweekly.com/feed/` | expansion | 电子行业媒体 feed，适合补充欧洲产业动态 |
| `https://www.servethehome.com/feed/` | expansion | 数据中心与服务器硬件 feed，适合补充 AI 基础设施信号 |
| `https://news.google.com/rss/search?q=semiconductor%20OR%20memory%20OR%20HBM&hl=en-US&gl=US&ceid=US:en` | expansion | Google News 聚合源，覆盖广，但必须作为 optional 使用 |
| `https://news.google.com/rss/search?q=NVIDIA%20OR%20Micron%20OR%20SK%20hynix%20OR%20TSMC&hl=en-US&gl=US&ceid=US:en` | expansion | Google News 聚合源，适合补厂商舆情面，但噪音和重复更高 |
| `https://export.arxiv.org/rss/cs.AR` | expansion | 研究向 RSS，适合补充技术前沿，不适合作为默认底座 |

有意不放进默认模板的候选：

| Feed | 原因 |
| --- | --- |
| `https://export.arxiv.org/rss/cs.LG` | 当前环境返回真 RSS，但响应体约 1.9MiB，超过插件 schema 的 `max_response_bytes` 上限 `1048576` |
| `https://www.digitimes.com/rss/daily.xml` | 当前环境可访问，但条目量更大，V1 先不放进默认 optional 模板 |
| `https://www.anandtech.com/rss/` | 当前环境会落到 HTML 页面，不是真 feed |
| `https://investor.amd.com/rss/news-releases.xml` | 当前环境 TLS 握手不稳定，不适合作为默认模板源 |

### optional Readability enrichment

`quantagent.official.source.readability` 被声明为 optional。

- 作用：表达行业包支持正文增强能力
- 模板：`templates/source_bindings/readability.default.yaml`
- 语义：缺少它时允许 worker 走 degraded RSS-summary 主链路，而不是让行业包自己抓正文

## 模板里应该放什么

- 可公开的 baseline / expansion feed 列表
- 非敏感过滤条件，例如关键词、分类、source 标签
- 正文增强相关的默认阈值，例如 `min_text_length`

说明：

- `keywords` 现在已经会被 RSS 插件消费，但只是轻量包含匹配：
  - 命中 title / content / url 任一字段时保留该 entry
  - 不做语义分类，不做模型判断，也不保证多语言召回完整
- Google News RSS 当前环境可抓，但它是聚合源：
  - 适合作为 optional expansion
  - 不适合作为 baseline required/default-enabled

## 模板里不要放什么

- secret 明文、token、私有账户、生产凭证
- `effective_config`
- `binding_id`
- `status`、`last_run_at`、`next_run_at`
- 调度计数、失败统计、审计字段
- 任何试图让行业包自己承担 scheduler / worker 职责的运行态字段

## 最小验证

在仓库根目录执行：

```bash
uv run python -m unittest packages/core/tests/test_registry.py
```

这里的验证目标是确认 Registry 能稳定读取半导体行业包的 `source_bindings` 元信息，而不是验证行业分析闭环。

## 运行备注

- 只启动 `uv run api` 不会触发这些 RSS 模板。
- 要实际抓 RSS，需要单独启动 `scheduler`；要继续走 Readability 和 `industry.analysis.requested`，还需要单独启动 `worker`。
- 默认 `EVENT_BUS_BACKEND=memory` 只适合单进程 smoke；`scheduler` 和 `worker` 分开进程验证时必须改用 Kafka。
- 2026-06-02 在当前开发环境里，`Micron`、`Marvell`、`SemiEngineering` 已通过真实 `scheduler.run_once()` smoke；`NVIDIA` 也已验证可抓，但需要把 `max_response_bytes` 提高到 `1048576`。

# quantagent-demo CLI 操作指南

`quantagent-demo` 是一个面向小白的最小演示命令，用来证明：

```text
官方插件被扫描到
-> source.fetch 被真实触发
-> source.event.captured 被发布
-> fake consumer 真的收到了这条消息
```

它不是业务主链演示，不会继续往 analysis / strategy / discord / approval / broker 走。

## 你会看到什么

运行成功时，会看到 4 段关键信息：

1. 扫描插件
2. 触发 `source.fetch`
3. 发布 `source.event.captured`
4. fake consumer 收到事件

## 一步一步操作

### 1. 进入仓库根目录

先确认你在 QuantAgent 仓库根目录：

```bash
pwd
```

你应该能看到当前目录下有这些路径：

```text
apps/
packages/
plugins/
openspec/
```

### 2. 运行演示命令

直接执行：

```bash
uv run quantagent-demo
```

### 3. 预期输出

正常情况下，你会看到类似下面的输出：

```text
🔍 Scanning plugins... found N plugin(s)
✅ quantagent.official.source.placeholder v0.1.0

🚀 Triggering plugin: source.fetch
Plugin: quantagent.official.source.placeholder
Status: SUCCEEDED ✓

📤 Event published to: source.event.captured
Event ID: evt_xxx
Items: 1 source item(s)

📩 Consumer received event!
Topic: source.event.captured
Payload: { plugin_id: "quantagent.official.source.placeholder", items: 1 }

✨ Demo complete! The full pipeline works.
```

看到这些输出，说明这条最小闭环已经通了：

```text
plugin -> scheduling -> event bus -> consumer
```

## 常见说明

### 为什么扫描到了很多插件，但只触发一个？

这是故意的。

demo 会真实扫描当前官方插件目录，所以你能看到现在仓库里已有的官方插件。
但真正执行时，只会触发：

```text
quantagent.official.source.placeholder
```

因为它是当前最稳定、最小、无外部依赖的官方 source 插件，最适合做基础闭环演示。

### 我本地设置过 Kafka 环境变量，会不会影响它？

不会。

这个 demo 会强制使用 `InMemoryEventBus`，即使你本地设置了：

```bash
EVENT_BUS_BACKEND=kafka
```

它也仍然走内存总线，不依赖 Kafka。

你可以手动验证：

```bash
EVENT_BUS_BACKEND=kafka uv run quantagent-demo
```

### 如果失败了怎么看？

只要 demo 失败：

- 命令会输出一个最小错误摘要
- 退出码不是 `0`

最常见的失败原因通常是：

- 你不在仓库根目录
- Python / uv 环境没准备好
- 本地工作区缺少必须依赖

## 这条 demo 不负责什么

为了避免误解，这里再强调一次：

- 不负责 analysis / strategy / approval / broker
- 不负责 Kafka / DB / 外部 provider
- 不负责完整业务主链

它只负责演示：

```text
最小插件调度到事件消费闭环
```

from __future__ import annotations

import asyncio
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from quantagent.core.events import EventBusError, InMemoryEventBus
from quantagent.core.events.kafka import KafkaEventBusConsumer, KafkaEventBusPublisher
from quantagent.core.scheduling import PluginRunStatus
from quantagent.scheduler.main import SchedulerRuntime, _run, create_scheduler_runtime


# ---- helpers ----

def _memory_env():
    """返回 memory 后端的环境变量 patch。"""
    return patch.dict("os.environ", {
        "EVENT_BUS_BACKEND": "memory",
        "EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS": "",
    }, clear=False)


def _kafka_env(bootstrap="localhost:9092"):
    """返回 kafka 后端的环境变量 patch。"""
    return patch.dict("os.environ", {
        "EVENT_BUS_BACKEND": "kafka",
        "EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS": bootstrap,
    }, clear=False)


# ---- Group 4: Memory 后端单元测试 ----

class TestMemoryBackend(unittest.TestCase):
    """task 4.1 / 4.2 / 4.3"""

    def test_memory_backend_assembly(self) -> None:
        """task 4.1: SchedulerRuntime 组装验证"""
        with _memory_env():
            runtime = create_scheduler_runtime()
        self.assertIsInstance(runtime, SchedulerRuntime)
        self.assertEqual(runtime.event_bus.backend, "memory")
        self.assertIsInstance(runtime.event_bus.publisher, InMemoryEventBus)
        # scheduling 实例持有 publisher
        self.assertIs(runtime.scheduling._source_publisher.publisher, runtime.event_bus.publisher)

    def test_memory_backend_scheduling_holds_publisher(self) -> None:
        """task 4.2: scheduling 实例正确持有 publisher"""
        with _memory_env():
            runtime = create_scheduler_runtime()
        self.assertIsNotNone(runtime.scheduling._source_publisher)
        self.assertIsInstance(runtime.scheduling._source_publisher.publisher, InMemoryEventBus)

    def test_memory_backend_event_published_to_handler(self) -> None:
        """task 4.3: 触发成功后通过 subscribe 捕获 source.event.captured"""
        with _memory_env():
            runtime = create_scheduler_runtime()

        captured = []

        async def _handler(envelope):
            captured.append(envelope)

        async def _test():
            bus = runtime.event_bus.publisher
            await bus.subscribe(topics=["source.event.captured"], group_id="test", handler=MagicMock(handle=AsyncMock(side_effect=_handler)))

            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="quantagent.official.source.placeholder",
                capability="source.fetch",
                request_id="req_test",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            record = await runtime.scheduling.trigger(request)
            self.assertEqual(record.status, PluginRunStatus.SUCCEEDED)
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0].topic, "source.event.captured")
            self.assertIn("plugin_id", captured[0].payload)

        asyncio.run(_test())


# ---- Group 5: Kafka 后端单元测试 ----

class TestKafkaBackend(unittest.TestCase):
    """task 5.1 / 5.2 / 5.3"""

    @patch("quantagent.scheduler.main.build_event_bus_runtime")
    def test_kafka_backend_assembly(self, mock_build) -> None:
        """task 5.1: Kafka 后端组装验证"""
        mock_publisher = MagicMock(spec=KafkaEventBusPublisher)
        mock_consumer = MagicMock(spec=KafkaEventBusConsumer)
        mock_runtime = MagicMock()
        mock_runtime.publisher = mock_publisher
        mock_runtime.consumer = mock_consumer
        mock_runtime.backend = "kafka"
        mock_build.return_value = mock_runtime

        with _kafka_env():
            runtime = create_scheduler_runtime()

        self.assertIsInstance(runtime, SchedulerRuntime)
        self.assertEqual(runtime.event_bus.backend, "kafka")
        self.assertIs(runtime.event_bus.publisher, mock_publisher)

    @patch("quantagent.core.events.kafka.KafkaEventBusPublisher._get_producer")
    def test_kafka_backend_publish_called_on_trigger(self, mock_get_producer) -> None:
        """task 5.2: Kafka 后端触发后 publish 被调用"""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()
        mock_get_producer.return_value = mock_producer

        with _kafka_env():
            runtime = create_scheduler_runtime()

        async def _test():
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="quantagent.official.source.placeholder",
                capability="source.fetch",
                request_id="req_kafka_test",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            record = await runtime.scheduling.trigger(request)
            self.assertEqual(record.status, PluginRunStatus.SUCCEEDED)
            # publish 被调用
            mock_producer.send_and_wait.assert_called_once()
            call_args = mock_producer.send_and_wait.call_args
            topic = call_args[0][0]
            self.assertEqual(topic, "source.event.captured")

        asyncio.run(_test())

    def test_kafka_config_missing_raises(self) -> None:
        """task 5.3: BOOTSTRAP_SERVERS 为空时抛出 EventBusError"""
        with patch.dict("os.environ", {
            "EVENT_BUS_BACKEND": "kafka",
            "EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS": "",
        }, clear=False):
            with self.assertRaises(EventBusError) as ctx:
                create_scheduler_runtime()
            self.assertEqual(ctx.exception.code, "EVENT_BUS_KAFKA_CONFIG_MISSING")


# ---- Group 6: 边界与错误路径测试 ----

class TestEdgeCases(unittest.TestCase):
    """task 6.1 / 6.2 / 6.3"""

    def test_plugin_not_found_returns_failed(self) -> None:
        """task 6.1: 插件未注册时 trigger 返回 FAILED"""
        with _memory_env():
            runtime = create_scheduler_runtime()

        async def _test():
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="nonexistent.plugin.id",
                capability="source.fetch",
                request_id="req_notfound",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            record = await runtime.scheduling.trigger(request)
            self.assertEqual(record.status, PluginRunStatus.FAILED)
            self.assertIsNotNone(record.error_summary)

        asyncio.run(_test())

    def test_close_called_on_failure(self) -> None:
        """task 6.2: 触发失败时仍调用 runtime.close()"""
        with _memory_env():
            runtime = create_scheduler_runtime()

        async def _test():
            # 用不存在的插件触发失败
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="nonexistent.plugin.id",
                capability="source.fetch",
                request_id="req_close_test",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            record = await runtime.scheduling.trigger(request)
            self.assertEqual(record.status, PluginRunStatus.FAILED)
            # close 不抛异常
            await runtime.close()

        asyncio.run(_test())

    @patch("quantagent.scheduler.main.sys.exit")
    def test_structured_log_output(self, mock_exit) -> None:
        """task 6.3: 结构化日志输出包含正确字段"""
        with _memory_env():
            with self.assertLogs("quantagent.scheduler.main", level="INFO") as cm:
                asyncio.run(_run())

            # 验证 log record 的 extra 属性包含结构化字段
            log_record = cm.records[-1]
            self.assertEqual(log_record.status, "succeeded")
            self.assertIsNotNone(log_record.duration_ms)
            self.assertEqual(log_record.plugin_id, "quantagent.official.source.placeholder")
            self.assertEqual(log_record.capability, "source.fetch")
            mock_exit.assert_called_once_with(0)


# ---- Group 7: Kafka 异常处理测试 ----

class TestKafkaErrorHandling(unittest.TestCase):
    """task 7.1 / 7.2 / 7.3"""

    @patch("quantagent.core.events.kafka.KafkaEventBusPublisher._get_producer")
    def test_publish_failure_does_not_affect_run_status(self, mock_get_producer) -> None:
        """task 7.1: Kafka 发布失败不影响 PluginRunRecord 状态"""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(side_effect=EventBusError(
            code="EVENT_PUBLISH_FAILED",
            message="Kafka publish failed.",
            stage="publish",
        ))
        mock_get_producer.return_value = mock_producer

        with _kafka_env():
            runtime = create_scheduler_runtime()

        async def _test():
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="quantagent.official.source.placeholder",
                capability="source.fetch",
                request_id="req_publish_fail",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            record = await runtime.scheduling.trigger(request)
            # 调度成功，发布失败不影响状态
            self.assertEqual(record.status, PluginRunStatus.SUCCEEDED)

        asyncio.run(_test())

    @patch("quantagent.core.events.kafka.KafkaEventBusPublisher._get_producer")
    def test_publish_failure_logs_warning(self, mock_get_producer) -> None:
        """task 7.2: Kafka 发布失败时 warning 日志包含 run_id 和 plugin_id"""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(side_effect=EventBusError(
            code="EVENT_PUBLISH_FAILED",
            message="Kafka publish failed.",
            stage="publish",
        ))
        mock_get_producer.return_value = mock_producer

        with _kafka_env():
            runtime = create_scheduler_runtime()

        async def _test():
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="quantagent.official.source.placeholder",
                capability="source.fetch",
                request_id="req_warn_log",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            with self.assertLogs("quantagent.core.scheduling.service", level="WARNING") as cm:
                record = await runtime.scheduling.trigger(request)

            self.assertEqual(record.status, PluginRunStatus.SUCCEEDED)
            # warning log record 的 extra 属性包含关键字段
            warning_record = cm.records[-1]
            self.assertEqual(warning_record.run_id, record.run_id)
            self.assertEqual(warning_record.plugin_id, "quantagent.official.source.placeholder")

        asyncio.run(_test())

    @patch("quantagent.core.events.kafka.KafkaEventBusPublisher._get_producer")
    def test_close_does_not_raise(self, mock_get_producer) -> None:
        """task 7.3: Kafka 后端 close() 正常清理不抛异常"""
        mock_producer = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_get_producer.return_value = mock_producer

        with _kafka_env():
            runtime = create_scheduler_runtime()

        async def _test():
            # 先触发一次让 producer 初始化
            request = __import__("quantagent.core.scheduling", fromlist=["PluginTriggerRequest"]).PluginTriggerRequest(
                plugin_id="quantagent.official.source.placeholder",
                capability="source.fetch",
                request_id="req_close",
                trigger_type=__import__("quantagent.core.scheduling", fromlist=["PluginTriggerType"]).PluginTriggerType.MANUAL,
            )
            await runtime.scheduling.trigger(request)
            # close 不抛异常
            await runtime.close()

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()

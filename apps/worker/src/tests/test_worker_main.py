from __future__ import annotations

import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.core.event_intake import ModelConfigStructuredModelInvoker, ReviewOnlyStructuredModelInvoker
from quantagent.worker.main import (
    _build_analysis_processing_scope_factory,
    create_worker_app,
    create_worker_runtime,
    run,
    run_forever,
    run_once,
)


class WorkerMainTestCase(unittest.IsolatedAsyncioTestCase):
    def test_worker_runtime_uses_memory_backend_when_explicitly_overridden(self) -> None:
        with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_worker_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)

    def test_create_worker_app_requires_database_url(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", None):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
                create_worker_app()

    def test_create_worker_app_builds_handler_when_database_url_exists(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_worker_app()
        self.assertEqual(app.runtime.backend, "memory")
        self.assertIsNotNone(app.handler)
        self.assertIsNotNone(app.analysis_request_handler)
        app.session.close()

    def test_create_worker_app_uses_topic_publishing_gateway(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_worker_app()
        gateway = app.handler.routing_service._industry_gateway
        self.assertEqual(gateway.__class__.__name__, "TopicPublishingIndustryGateway")
        app.session.close()

    def test_create_worker_app_uses_review_only_invoker_without_encryption_key(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                with patch("quantagent.worker.main.settings.MODEL_CONFIG_ENCRYPTION_KEY", None):
                    app = create_worker_app()
        self.assertIsInstance(app.analysis_request_handler.runner._invoker, ReviewOnlyStructuredModelInvoker)
        app.session.close()

    def test_create_worker_app_uses_model_config_invoker_when_encryption_key_exists(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                with patch("quantagent.worker.main.settings.MODEL_CONFIG_ENCRYPTION_KEY", "test-key"):
                    app = create_worker_app()
        self.assertIsInstance(app.analysis_request_handler.runner._invoker, ModelConfigStructuredModelInvoker)
        app.session.close()

    def test_analysis_processing_scope_uses_separate_model_and_routed_sessions(self) -> None:
        sessions: list[_FakeSession] = []

        def session_factory() -> _FakeSession:
            session = _FakeSession(name=f"session-{len(sessions)}")
            sessions.append(session)
            return session

        with patch("quantagent.worker.main.settings.MODEL_CONFIG_ENCRYPTION_KEY", "test-key"):
            scope = _build_analysis_processing_scope_factory(session_factory)()

        invoker = scope.runner._invoker
        self.assertIsInstance(invoker, ModelConfigStructuredModelInvoker)
        self.assertEqual(len(sessions), 1)
        routed_session = sessions[0]

        service = invoker.service_factory()
        self.assertEqual(len(sessions), 2)
        model_session = sessions[1]
        self.assertIsNot(model_session, routed_session)

        invoker.close_service(service)
        scope.close()

        self.assertTrue(model_session.closed)
        self.assertTrue(routed_session.closed)

    async def test_consume_once_subscribes_source_and_analysis_request_topics(self) -> None:
        app = _SubscribingWorkerApp()

        await app.consume_once()

        self.assertEqual(len(app.runtime.consumer.subscriptions), 1)
        topics, group_id, handler = app.runtime.consumer.subscriptions[0]
        self.assertEqual(topics, ("source.event.captured", "industry.analysis.requested"))
        self.assertEqual(group_id, "group")
        self.assertEqual(handler.__class__.__name__, "_TopicDispatchHandler")

    async def test_consume_forever_subscribes_source_and_analysis_request_topics(self) -> None:
        app = _SubscribingWorkerApp()

        await app.consume_forever()

        self.assertEqual(len(app.runtime.consumer.forever_subscriptions), 1)
        topics, group_id, handler = app.runtime.consumer.forever_subscriptions[0]
        self.assertEqual(topics, ("source.event.captured", "industry.analysis.requested"))
        self.assertEqual(group_id, "group")
        self.assertEqual(handler.__class__.__name__, "_TopicDispatchHandler")

    async def test_run_once_consumes_once_and_closes_app(self) -> None:
        app = _FakeWorkerApp()
        with patch("quantagent.worker.main.create_worker_app", return_value=app):
            await run_once()

        self.assertEqual(app.consumed_once, 1)
        self.assertEqual(app.closed, 1)

    async def test_run_forever_consumes_forever_and_closes_app(self) -> None:
        app = _FakeWorkerApp()
        with patch("quantagent.worker.main.create_worker_app", return_value=app):
            await run_forever()

        self.assertEqual(app.consumed_forever, 1)
        self.assertEqual(app.closed, 1)

    def test_run_executes_run_forever(self) -> None:
        calls = []

        async def fake_run_forever() -> None:
            calls.append("run_forever")

        with patch("quantagent.worker.main.run_forever", fake_run_forever):
            run()

        self.assertEqual(calls, ["run_forever"])


class _FakeWorkerApp:
    consumed_once = 0
    consumed_forever = 0
    closed = 0

    async def consume_once(self) -> None:
        self.consumed_once += 1

    async def consume_forever(self) -> None:
        self.consumed_forever += 1

    async def close(self) -> None:
        self.closed += 1


class _FakeSession:
    def __init__(self, *, name: str) -> None:
        self.name = name
        self.closed = False

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class _RecordingConsumer:
    def __init__(self) -> None:
        self.subscriptions = []
        self.forever_subscriptions = []

    async def subscribe(self, *, topics, group_id, handler):
        self.subscriptions.append((tuple(topics), group_id, handler))

    async def consume_forever(self, *, topics, group_id, handler):
        self.forever_subscriptions.append((tuple(topics), group_id, handler))


class _SubscribingWorkerApp:
    def __init__(self) -> None:
        self.handler = object()
        self.analysis_request_handler = object()
        self.runtime = type("Runtime", (), {"consumer": _RecordingConsumer()})()

    async def consume_once(self) -> None:
        from quantagent.worker.main import WorkerApp

        worker_app = WorkerApp(
            runtime=self.runtime,
            handler=self.handler,
            analysis_request_handler=self.analysis_request_handler,
            session=object(),
        )
        with patch("quantagent.worker.main.settings.EVENT_BUS_KAFKA_DEFAULT_GROUP_ID", "group"):
            await worker_app.consume_once()

    async def consume_forever(self) -> None:
        from quantagent.worker.main import WorkerApp

        worker_app = WorkerApp(
            runtime=self.runtime,
            handler=self.handler,
            analysis_request_handler=self.analysis_request_handler,
            session=object(),
        )
        with patch("quantagent.worker.main.settings.EVENT_BUS_KAFKA_DEFAULT_GROUP_ID", "group"):
            await worker_app.consume_forever()


if __name__ == "__main__":
    unittest.main()

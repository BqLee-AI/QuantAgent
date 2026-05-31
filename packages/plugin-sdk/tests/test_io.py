from __future__ import annotations

import unittest

from quantagent.plugin_sdk import (
    AnalysisInput,
    AnalysisResult,
    BrokerExecuteInput,
    BrokerExecuteResult,
    DTO_VALIDATION_ERROR_CODE,
    EvidenceExtractResult,
    EvidenceItem,
    EvidenceLike,
    EvidenceSearchResult,
    NotificationSendInput,
    NotificationSendResult,
    PluginRuntimeError,
    SourceFetchInput,
    SourceFetchResult,
    SourceItemDraft,
    StrategyDraftInput,
    StrategyDraftResult,
    freeze_json_mapping,
)


class PluginSdkIoDtoTestCase(unittest.TestCase):
    def test_source_fetch_input_can_roundtrip_mapping_and_keeps_metadata_read_only(self) -> None:
        payload = {
            "query": "oil",
            "limit": 10,
            "cursor": "cursor-1",
            "metadata": {"source": "rss", "flags": ["fresh", True], "page": {"index": 1}},
        }

        dto = SourceFetchInput.from_mapping(payload)

        self.assertEqual(dto.query, "oil")
        self.assertEqual(dto.limit, 10)
        self.assertEqual(dto.cursor, "cursor-1")
        self.assertEqual(dto.to_mapping(), payload)
        with self.assertRaises(TypeError):
            dto.metadata["new"] = "value"  # type: ignore[index]

    def test_source_fetch_result_serializes_multiple_items(self) -> None:
        first = SourceItemDraft(
            external_id="a-1",
            title="Alpha",
            raw_payload={"score": 1, "tags": ["rss"]},
            metadata={"rank": 1},
        )
        second = SourceItemDraft(
            external_id="b-2",
            url="https://example.com/b-2",
            content="body",
            published_at="2026-05-27T00:00:00Z",
            metadata={"rank": 2},
        )

        result = SourceFetchResult(
            items=[first, second],
            next_cursor="cursor-2",
            metadata={"count": 2},
        )

        self.assertEqual(len(result.items), 2)
        self.assertEqual(
            result.to_mapping(),
            {
                "items": [
                    {
                        "external_id": "a-1",
                        "url": None,
                        "title": "Alpha",
                        "content": None,
                        "author": None,
                        "published_at": None,
                        "captured_at": None,
                        "raw_payload": {"score": 1, "tags": ["rss"]},
                        "metadata": {"rank": 1},
                    },
                    {
                        "external_id": "b-2",
                        "url": "https://example.com/b-2",
                        "title": None,
                        "content": "body",
                        "author": None,
                        "published_at": "2026-05-27T00:00:00Z",
                        "captured_at": None,
                        "raw_payload": {},
                        "metadata": {"rank": 2},
                    },
                ],
                "next_cursor": "cursor-2",
                "metadata": {"count": 2},
            },
        )

    def test_source_fetch_result_can_roundtrip_empty_result(self) -> None:
        payload = {"items": [], "next_cursor": None, "metadata": {"empty": True}}

        result = SourceFetchResult.from_mapping(payload)

        self.assertEqual(result.items, ())
        self.assertEqual(result.to_mapping(), payload)

    def test_notification_send_input_and_rejected_result_roundtrip(self) -> None:
        request = NotificationSendInput.from_mapping(
            {
                "channel": "discord",
                "text": "rate limited",
                "severity": "warning",
                "recipient": "ops-room",
                "metadata": {"attempt": 3},
            }
        )
        result = NotificationSendResult.from_mapping(
            {
                "accepted": False,
                "provider_message_id": None,
                "retryable": True,
                "metadata": {"provider_status": 429},
            }
        )

        self.assertEqual(
            request.to_mapping(),
            {
                "channel": "discord",
                "text": "rate limited",
                "severity": "warning",
                "recipient": "ops-room",
                "metadata": {"attempt": 3},
            },
        )
        self.assertEqual(
            result.to_mapping(),
            {
                "accepted": False,
                "provider_message_id": None,
                "retryable": True,
                "metadata": {"provider_status": 429},
            },
        )
        with self.assertRaises(TypeError):
            result.metadata["another"] = 1  # type: ignore[index]

    def test_json_safe_validation_rejects_unserializable_values(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceItemDraft(raw_payload={"bad": object()})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.stage, "invoke")
        self.assertEqual(raised.exception.details["value_type"], "object")

    def test_json_safe_validation_rejects_non_finite_numbers(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceFetchInput(metadata={"score": float("nan")})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["value_type"], "float")

    def test_source_fetch_result_requires_items_in_mapping(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            SourceFetchResult.from_mapping({"metadata": {}})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["field"], "items")

    def test_from_mapping_uses_structured_error_for_invalid_payload(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            NotificationSendInput.from_mapping(
                {
                    "channel": "discord",
                    "text": 123,
                    "metadata": {"path": "/home/xxs/private"},
                },
                stage="config",
            )

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.stage, "config")
        self.assertEqual(raised.exception.details["field"], "text")

    def test_freeze_json_mapping_rejects_non_string_keys(self) -> None:
        with self.assertRaises(PluginRuntimeError) as raised:
            freeze_json_mapping({1: "invalid"})

        self.assertEqual(raised.exception.code, DTO_VALIDATION_ERROR_CODE)
        self.assertEqual(raised.exception.details["key_type"], "int")

    def test_evidence_item_roundtrip(self) -> None:
        original = EvidenceItem(
            title="Evidence title",
            url="https://example.com/evidence",
            snippet="This is a snippet",
            score=0.9,
            source="Example Source",
            published_at="2026-05-31T00:00:00Z",
            favicon_url="https://example.com/favicon.ico",
            metadata={"provider": "tavily"},
        )
        mapped = original.to_mapping()
        restored = EvidenceItem.from_mapping(mapped)
        self.assertEqual(restored.title, "Evidence title")
        self.assertEqual(restored.url, "https://example.com/evidence")
        self.assertEqual(restored.score, 0.9)
        self.assertEqual(restored.metadata["provider"], "tavily")

    def test_evidence_search_result_roundtrip(self) -> None:
        original = EvidenceSearchResult(
            query="test query",
            results=(
                EvidenceItem(title="Test", url="https://example.com", score=0.9),
                EvidenceItem(title="Another", url="https://example.org", score=0.8),
            ),
            metadata={"provider": "tavily"},
        )
        mapped = original.to_mapping()
        restored = EvidenceSearchResult.from_mapping(mapped)
        self.assertEqual(restored.query, "test query")
        self.assertEqual(len(restored.results), 2)
        self.assertEqual(restored.results[0].title, "Test")
        self.assertEqual(restored.metadata["provider"], "tavily")

    def test_evidence_extract_result_roundtrip(self) -> None:
        original = EvidenceExtractResult(
            url="https://example.com/article",
            title="Article Title",
            content="Article content",
            raw_content="<html>Raw HTML</html>",
            metadata={"extracted_at": "2026-05-31"},
        )
        mapped = original.to_mapping()
        restored = EvidenceExtractResult.from_mapping(mapped)
        self.assertEqual(restored.url, "https://example.com/article")
        self.assertEqual(restored.title, "Article Title")
        self.assertEqual(restored.content, "Article content")
        self.assertEqual(restored.metadata["extracted_at"], "2026-05-31")

    def test_analysis_input_roundtrip(self) -> None:
        original = AnalysisInput(
            evidences=(
                EvidenceItem(title="Evidence 1", url="https://example.com/1"),
                EvidenceItem(title="Evidence 2", url="https://example.com/2"),
            ),
            query="What is the market trend?",
            metadata={"context": "investment"},
        )
        mapped = original.to_mapping()
        restored = AnalysisInput.from_mapping(mapped)
        self.assertEqual(len(restored.evidences), 2)
        # from_mapping 将 plain mapping 重建为 EvidenceItem
        self.assertEqual(restored.evidences[0].title, "Evidence 1")
        self.assertEqual(restored.query, "What is the market trend?")
        self.assertEqual(restored.metadata["context"], "investment")

    def test_analysis_result_roundtrip(self) -> None:
        original = AnalysisResult(
            summary="Market is bullish",
            key_facts=("Fact 1", "Fact 2"),
            market_impact="High",
            direction="up",
            confidence=0.85,
            uncertainty=("Risk factor 1",),
            evidence_refs=("ref1", "ref2"),
            metadata={"model": "gpt-4"},
        )
        mapped = original.to_mapping()
        restored = AnalysisResult.from_mapping(mapped)
        self.assertEqual(restored.summary, "Market is bullish")
        self.assertEqual(restored.key_facts, ("Fact 1", "Fact 2"))
        self.assertEqual(restored.confidence, 0.85)
        self.assertEqual(restored.metadata["model"], "gpt-4")

    def test_strategy_draft_input_roundtrip(self) -> None:
        original = StrategyDraftInput(
            analysis={"summary": "Bullish market", "confidence": 0.9},
            metadata={"strategy_type": "momentum"},
        )
        mapped = original.to_mapping()
        restored = StrategyDraftInput.from_mapping(mapped)
        self.assertEqual(restored.analysis["summary"], "Bullish market")
        self.assertEqual(restored.metadata["strategy_type"], "momentum")

    def test_strategy_draft_result_roundtrip(self) -> None:
        original = StrategyDraftResult(
            action="buy",
            symbol="AAPL",
            direction="long",
            time_horizon="1w",
            rationale="Strong earnings",
            risk_notes=("Market volatility", "Sector risk"),
            confidence=0.8,
            requires_approval=True,
            metadata={"risk_level": "medium"},
        )
        mapped = original.to_mapping()
        restored = StrategyDraftResult.from_mapping(mapped)
        self.assertEqual(restored.action, "buy")
        self.assertEqual(restored.symbol, "AAPL")
        self.assertEqual(restored.risk_notes, ("Market volatility", "Sector risk"))
        self.assertEqual(restored.confidence, 0.8)
        self.assertEqual(restored.metadata["risk_level"], "medium")

    def test_broker_execute_input_roundtrip(self) -> None:
        original = BrokerExecuteInput(
            action="buy",
            symbol="AAPL",
            quantity=100.0,
            order_type="limit",
            price=150.0,
            dry_run=True,
            metadata={"account": "demo"},
        )
        mapped = original.to_mapping()
        restored = BrokerExecuteInput.from_mapping(mapped)
        self.assertEqual(restored.action, "buy")
        self.assertEqual(restored.symbol, "AAPL")
        self.assertEqual(restored.quantity, 100.0)
        self.assertEqual(restored.dry_run, True)
        self.assertEqual(restored.metadata["account"], "demo")

    def test_broker_execute_result_roundtrip(self) -> None:
        original = BrokerExecuteResult(
            status="validated",
            estimated_order={"symbol": "AAPL", "quantity": 100, "price": 150.0},
            validation_errors=(),
            audit_hints=("Check account balance",),
            metadata={"broker": "ibkr"},
        )
        mapped = original.to_mapping()
        restored = BrokerExecuteResult.from_mapping(mapped)
        self.assertEqual(restored.status, "validated")
        self.assertEqual(restored.estimated_order["symbol"], "AAPL")
        self.assertEqual(restored.audit_hints, ("Check account balance",))
        self.assertEqual(restored.metadata["broker"], "ibkr")

    # -- 负面测试：验证 from_mapping 对非法输入的正确拒绝 --

    def test_evidence_search_result_rejects_missing_query(self) -> None:
        """EvidenceSearchResult.from_mapping 缺少 query 必须抛 dto_validation_error"""
        with self.assertRaises(PluginRuntimeError) as cm:
            EvidenceSearchResult.from_mapping({"results": []})
        self.assertEqual(cm.exception.code, DTO_VALIDATION_ERROR_CODE)

    def test_analysis_input_rejects_non_array_evidences(self) -> None:
        """AnalysisInput.from_mapping evidences 不是数组必须抛 dto_validation_error"""
        with self.assertRaises(PluginRuntimeError) as cm:
            AnalysisInput.from_mapping({"evidences": "not_array"})
        self.assertEqual(cm.exception.code, DTO_VALIDATION_ERROR_CODE)

    def test_analysis_input_accepts_evidence_like_protocol(self) -> None:
        """AnalysisInput 接受满足 EvidenceLike Protocol 的自定义对象"""
        class CustomEvidence:
            @property
            def title(self) -> str | None:
                return "Custom"
            @property
            def url(self) -> str | None:
                return "https://custom.com"
            @property
            def snippet(self) -> str | None:
                return "Custom snippet"

        custom = CustomEvidence()
        self.assertIsInstance(custom, EvidenceLike)
        original = AnalysisInput(evidences=(custom,))
        self.assertEqual(len(original.evidences), 1)
        self.assertEqual(original.evidences[0].title, "Custom")

    def test_analysis_input_rejects_non_evidence_like(self) -> None:
        """AnalysisInput.__post_init__ 拒绝不满足 EvidenceLike 的对象"""
        with self.assertRaises(PluginRuntimeError) as cm:
            AnalysisInput(evidences=("not_an_evidence",))
        self.assertEqual(cm.exception.code, DTO_VALIDATION_ERROR_CODE)

    def test_broker_execute_input_rejects_non_string_action(self) -> None:
        """BrokerExecuteInput.from_mapping action 不是字符串必须抛 dto_validation_error"""
        with self.assertRaises(PluginRuntimeError) as cm:
            BrokerExecuteInput.from_mapping({"action": 123, "symbol": "AAPL"})
        self.assertEqual(cm.exception.code, DTO_VALIDATION_ERROR_CODE)

    def test_broker_execute_result_rejects_missing_status(self) -> None:
        """BrokerExecuteResult.from_mapping 缺少 status 必须抛 dto_validation_error"""
        with self.assertRaises(PluginRuntimeError) as cm:
            BrokerExecuteResult.from_mapping({})
        self.assertEqual(cm.exception.code, DTO_VALIDATION_ERROR_CODE)

    def test_strategy_draft_result_defaults_requires_approval_to_true(self) -> None:
        """StrategyDraftResult.from_mapping 缺少 requires_approval 时默认 True"""
        result = StrategyDraftResult.from_mapping({"action": "buy", "rationale": "test"})
        self.assertTrue(result.requires_approval)

    def test_strategy_draft_result_explicit_requires_approval_false(self) -> None:
        """StrategyDraftResult.from_mapping 显式设 requires_approval=False"""
        result = StrategyDraftResult.from_mapping({"action": "buy", "rationale": "test", "requires_approval": False})
        self.assertFalse(result.requires_approval)

    def test_broker_execute_input_defaults_dry_run_to_true(self) -> None:
        """BrokerExecuteInput.from_mapping 缺少 dry_run 时默认 True"""
        result = BrokerExecuteInput.from_mapping({"action": "buy", "symbol": "AAPL"})
        self.assertTrue(result.dry_run)

    def test_broker_execute_input_explicit_dry_run_false(self) -> None:
        """BrokerExecuteInput.from_mapping 显式设 dry_run=False"""
        result = BrokerExecuteInput.from_mapping({"action": "buy", "symbol": "AAPL", "dry_run": False})
        self.assertFalse(result.dry_run)


if __name__ == "__main__":
    unittest.main()

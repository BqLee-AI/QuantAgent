from __future__ import annotations

import unittest

from sqlalchemy import create_engine

from quantagent.core.db.base import Base
from quantagent.core.model_config import (
    FixedModelCallClient,
    ModelConfigCrypto,
    ModelConfigKeyStatus,
    ModelConfigService,
    ModelConfigServiceError,
    ModelConfigStatus,
    ModelInvocationStatus,
    ModelTokenUsage,
    SaveModelConfigInput,
)
from quantagent.core.model_config.service import ModelCallResult


class FakeModelClient(FixedModelCallClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    def run_fixed_smoke(
        self,
        *,
        base_url: str | None,
        model: str,
        api_key: str,
        request_id: str | None,
    ) -> ModelCallResult:
        self.calls.append(
            {
                "base_url": base_url,
                "model": model,
                "api_key": api_key,
                "request_id": request_id,
            }
        )
        return ModelCallResult(
            token_usage=ModelTokenUsage(
                prompt_tokens=3,
                completion_tokens=1,
                total_tokens=4,
            )
        )


class ModelConfigServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = self._session()
        self.encryption_key = ModelConfigCrypto.generate_key()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_empty_config_is_missing_key_and_does_not_expose_secret(self) -> None:
        result = ModelConfigService(self.session, encryption_key=self.encryption_key).get_config()

        self.assertEqual(result.status, ModelConfigStatus.MISSING_KEY)
        self.assertEqual(result.key_status, ModelConfigKeyStatus.MISSING)
        self.assertIsNone(result.masked_key)

    def test_save_config_encrypts_key_and_query_returns_masked_state(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)

        result = service.save_config(
            SaveModelConfigInput(
                name="Local Gateway",
                base_url="http://127.0.0.1:11434/v1",
                model="qwen-test",
                api_key="sk-test-secret",
            )
        )

        self.assertEqual(result.status, ModelConfigStatus.CONFIGURED)
        self.assertEqual(result.key_status, ModelConfigKeyStatus.CONFIGURED)
        self.assertEqual(result.masked_key, "********")
        row = self.session.execute(Base.metadata.tables["model_configs"].select()).mappings().one()
        self.assertNotEqual(row["encrypted_api_key"], "sk-test-secret")
        self.assertNotIn("sk-test-secret", str(result))

    def test_missing_encryption_key_blocks_secret_save(self) -> None:
        service = ModelConfigService(self.session, encryption_key=None)

        with self.assertRaises(ModelConfigServiceError) as context:
            service.save_config(
                SaveModelConfigInput(
                    name="OpenAI",
                    model="gpt-test",
                    api_key="sk-secret",
                )
            )

        self.assertEqual(context.exception.code, "MODEL_CONFIG_ENCRYPTION_UNAVAILABLE")

    def test_test_connection_decrypts_key_and_records_usage(self) -> None:
        client = FakeModelClient()
        service = ModelConfigService(self.session, encryption_key=self.encryption_key, client=client)
        service.save_config(
            SaveModelConfigInput(
                name="Gateway",
                base_url="http://gateway/v1",
                model="demo-model",
                api_key="sk-runtime-secret",
            )
        )

        invocation = service.test_connection(request_id="req-model")

        self.assertEqual(invocation.status, ModelInvocationStatus.SUCCEEDED)
        self.assertEqual(invocation.token_usage.total_tokens, 4)
        self.assertEqual(client.calls[0]["api_key"], "sk-runtime-secret")
        self.assertEqual(client.calls[0]["request_id"], "req-model")
        invocations = service.list_invocations()
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0].request_id, "req-model")

    def test_disabled_config_does_not_call_provider_and_records_failure(self) -> None:
        client = FakeModelClient()
        service = ModelConfigService(self.session, encryption_key=self.encryption_key, client=client)
        service.save_config(
            SaveModelConfigInput(
                name="Gateway",
                model="demo-model",
                api_key="sk-secret",
                enabled=False,
            )
        )

        with self.assertRaises(ModelConfigServiceError) as context:
            service.test_connection(request_id="req-disabled")

        self.assertEqual(context.exception.code, "MODEL_CONFIG_DISABLED")
        self.assertEqual(client.calls, [])
        invocations = service.list_invocations()
        self.assertEqual(invocations[0].status, ModelInvocationStatus.FAILED)
        self.assertEqual(invocations[0].error_summary, "MODEL_CONFIG_DISABLED")

    def _session(self):
        from sqlalchemy.orm import sessionmaker

        return sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()


if __name__ == "__main__":
    unittest.main()

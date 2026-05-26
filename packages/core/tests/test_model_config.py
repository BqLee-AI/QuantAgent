from __future__ import annotations

import unittest

from sqlalchemy import create_engine

from quantagent.core.db.base import Base
from quantagent.core.model_config import (
    CreateModelProviderInput,
    CreateProviderModelInput,
    FixedModelCallClient,
    ModelConfigCrypto,
    ModelConfigService,
    ModelConfigServiceError,
    ModelInvocationStatus,
    ModelPresetKey,
    ModelPresetStatus,
    ModelResolutionSource,
    ModelTokenUsage,
    UpdateModelPresetInput,
    UpdateModelProviderInput,
    UpdateProviderModelInput,
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

    def test_empty_provider_list_has_no_default(self) -> None:
        result = ModelConfigService(self.session, encryption_key=self.encryption_key).list_providers()

        self.assertIsNone(result.default_provider_id)
        self.assertEqual(result.providers, [])

    def test_create_provider_encrypts_key_and_marks_first_provider_default(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)

        provider = service.create_provider(
            CreateModelProviderInput(
                name="Local Gateway",
                base_url="http://127.0.0.1:11434/v1",
                api_key="sk-test-secret",
            )
        )

        self.assertTrue(provider.is_default)
        row = self.session.execute(Base.metadata.tables["model_providers"].select()).mappings().one()
        self.assertNotEqual(row["encrypted_api_key"], "sk-test-secret")

    def test_missing_encryption_key_blocks_secret_save(self) -> None:
        service = ModelConfigService(self.session, encryption_key=None)

        with self.assertRaises(ModelConfigServiceError) as context:
            service.create_provider(
                CreateModelProviderInput(
                    name="OpenAI",
                    api_key="sk-secret",
                )
            )

        self.assertEqual(context.exception.code, "MODEL_CONFIG_ENCRYPTION_UNAVAILABLE")

    def test_can_switch_default_provider(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        first = service.create_provider(CreateModelProviderInput(name="First", api_key="sk-1"))
        second = service.create_provider(CreateModelProviderInput(name="Second", api_key="sk-2"))

        updated = service.set_default_provider(second.id)
        providers = service.list_providers().providers

        self.assertTrue(updated.is_default)
        by_id = {provider.id: provider for provider in providers}
        self.assertFalse(by_id[first.id].is_default)
        self.assertTrue(by_id[second.id].is_default)

    def test_provider_models_can_be_added_and_one_can_be_global_default(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        provider = service.create_provider(CreateModelProviderInput(name="Gateway", api_key="sk-1"))

        first_model = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="gpt-economy", is_global_default=True),
        )
        second_model = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="gpt-reasoner"),
        )

        detail = service.get_provider(provider.id)
        self.assertEqual(detail.model_count, 2)
        self.assertTrue(first_model.is_global_default)
        self.assertFalse(second_model.is_global_default)

    def test_updating_provider_model_can_move_global_default(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        provider = service.create_provider(CreateModelProviderInput(name="Gateway", api_key="sk-1"))
        first_model = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="gpt-economy", is_global_default=True),
        )
        second_model = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="gpt-reasoner"),
        )

        updated = service.update_provider_model(
            provider.id,
            second_model.id,
            UpdateProviderModelInput(
                model_name="gpt-reasoner",
                enabled=True,
                supports_vision=False,
                is_global_default=True,
            ),
        )
        detail = service.get_provider(provider.id)

        self.assertTrue(updated.is_global_default)
        by_id = {model.id: model for model in detail.models}
        self.assertFalse(by_id[first_model.id].is_global_default)
        self.assertTrue(by_id[second_model.id].is_global_default)

    def test_preset_binding_requires_primary_except_global_default(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)

        with self.assertRaises(ModelConfigServiceError) as context:
            service.update_preset(
                ModelPresetKey.ECONOMY_TEXT,
                UpdateModelPresetInput(primary_model_id=None, fallback_model_id=None),
            )

        self.assertEqual(context.exception.code, "MODEL_PRESET_PRIMARY_REQUIRED")

    def test_multimodal_preset_requires_vision_model(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        provider = service.create_provider(CreateModelProviderInput(name="Vision Gateway", api_key="sk-1"))
        text_only_model = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="text-only", supports_vision=False),
        )

        with self.assertRaises(ModelConfigServiceError) as context:
            service.update_preset(
                ModelPresetKey.MULTIMODAL,
                UpdateModelPresetInput(primary_model_id=text_only_model.id, fallback_model_id=None),
            )

        self.assertEqual(context.exception.code, "MODEL_PRESET_PRIMARY_INVALID")

    def test_resolve_preset_uses_fallback_then_global_default(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        provider = service.create_provider(CreateModelProviderInput(name="Gateway", api_key="sk-1"))
        primary = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="economy-primary", enabled=False),
        )
        fallback = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="economy-fallback"),
        )
        global_default = service.create_provider_model(
            provider.id,
            CreateProviderModelInput(model_name="global-default", is_global_default=True),
        )

        service.update_preset(
            ModelPresetKey.ECONOMY_TEXT,
            UpdateModelPresetInput(primary_model_id=primary.id, fallback_model_id=fallback.id),
        )
        resolved = service.resolve_preset_model(ModelPresetKey.ECONOMY_TEXT)
        self.assertEqual(resolved.source, ModelResolutionSource.FALLBACK)
        self.assertEqual(resolved.model.id, fallback.id)

        service.update_provider_model(
            provider.id,
            fallback.id,
            UpdateProviderModelInput(
                model_name="economy-fallback",
                enabled=False,
                supports_vision=False,
                is_global_default=False,
            ),
        )
        resolved_again = service.resolve_preset_model(ModelPresetKey.ECONOMY_TEXT)
        self.assertEqual(resolved_again.source, ModelResolutionSource.GLOBAL_DEFAULT)
        self.assertEqual(resolved_again.model.id, global_default.id)

    def test_list_presets_returns_fixed_categories(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)

        presets = service.list_presets()

        self.assertEqual(
            [preset.preset_key for preset in presets],
            [
                ModelPresetKey.ECONOMY_TEXT,
                ModelPresetKey.GENERAL_TEXT,
                ModelPresetKey.GLOBAL_DEFAULT,
                ModelPresetKey.MULTIMODAL,
                ModelPresetKey.REASONING_TEXT,
            ],
        )
        statuses = {preset.preset_key: preset.status for preset in presets}
        self.assertEqual(statuses[ModelPresetKey.GLOBAL_DEFAULT], ModelPresetStatus.CONFIGURED)
        self.assertEqual(statuses[ModelPresetKey.ECONOMY_TEXT], ModelPresetStatus.MISSING_PRIMARY)

    def test_test_connection_uses_first_enabled_provider_model_and_records_usage(self) -> None:
        client = FakeModelClient()
        service = ModelConfigService(self.session, encryption_key=self.encryption_key, client=client)
        provider = service.create_provider(
            CreateModelProviderInput(
                name="Gateway",
                base_url="http://gateway/v1",
                api_key="sk-runtime-secret",
            )
        )
        service.create_provider_model(provider.id, CreateProviderModelInput(model_name="demo-model"))

        invocation = service.test_connection(provider.id, request_id="req-model")

        self.assertEqual(invocation.status, ModelInvocationStatus.SUCCEEDED)
        self.assertEqual(invocation.provider_id, provider.id)
        self.assertEqual(invocation.token_usage.total_tokens, 4)
        self.assertEqual(client.calls[0]["api_key"], "sk-runtime-secret")
        self.assertEqual(client.calls[0]["model"], "demo-model")
        invocations = service.list_invocations(provider_id=provider.id)
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0].request_id, "req-model")
        self.assertEqual(invocations[0].preset_key, ModelPresetKey.GLOBAL_DEFAULT)

    def test_disabling_default_provider_promotes_next_enabled_provider(self) -> None:
        service = ModelConfigService(self.session, encryption_key=self.encryption_key)
        first = service.create_provider(CreateModelProviderInput(name="First", api_key="sk-1"))
        second = service.create_provider(CreateModelProviderInput(name="Second", api_key="sk-2"))

        service.update_provider(
            first.id,
            UpdateModelProviderInput(
                name="First",
                api_key=None,
                enabled=False,
            ),
        )

        providers = {provider.id: provider for provider in service.list_providers().providers}
        self.assertFalse(providers[first.id].is_default)
        self.assertTrue(providers[second.id].is_default)

    def _session(self):
        from sqlalchemy.orm import sessionmaker

        return sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)()


if __name__ == "__main__":
    unittest.main()

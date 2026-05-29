from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from quantagent.core.model_config.models import ModelPresetKey
from quantagent.core.model_config.orm import (
    ModelInvocationORM,
    ModelPresetBindingORM,
    ModelProviderModelORM,
    ModelProviderORM,
)


class ModelProviderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_provider(self, provider: ModelProviderORM) -> ModelProviderORM:
        self._session.add(provider)
        self._session.flush()
        return provider

    def get_provider(self, provider_id: int) -> ModelProviderORM | None:
        return self._session.get(ModelProviderORM, provider_id)

    def delete_provider(self, provider: ModelProviderORM) -> None:
        self._session.delete(provider)

    def list_providers(self) -> list[ModelProviderORM]:
        statement = select(ModelProviderORM).order_by(
            ModelProviderORM.is_default.desc(),
            ModelProviderORM.updated_at.desc(),
            ModelProviderORM.id.desc(),
        )
        return list(self._session.scalars(statement).all())

    def find_default_provider(self) -> ModelProviderORM | None:
        statement = select(ModelProviderORM).where(ModelProviderORM.is_default.is_(True)).limit(1)
        return self._session.scalars(statement).first()

    def clear_default_provider(self) -> None:
        for provider in self._session.scalars(select(ModelProviderORM).where(ModelProviderORM.is_default.is_(True))).all():
            provider.is_default = False

    def create_provider_model(self, model: ModelProviderModelORM) -> ModelProviderModelORM:
        self._session.add(model)
        self._session.flush()
        return model

    def get_provider_model(self, model_id: int) -> ModelProviderModelORM | None:
        return self._session.get(ModelProviderModelORM, model_id)

    def list_provider_models(self, provider_id: int) -> list[ModelProviderModelORM]:
        statement = (
            select(ModelProviderModelORM)
            .where(ModelProviderModelORM.provider_id == provider_id)
            .order_by(
                ModelProviderModelORM.is_global_default.desc(),
                ModelProviderModelORM.enabled.desc(),
                ModelProviderModelORM.updated_at.desc(),
                ModelProviderModelORM.id.desc(),
            )
        )
        return list(self._session.scalars(statement).all())

    def delete_provider_model(self, model: ModelProviderModelORM) -> None:
        self._session.delete(model)

    def clear_global_default_model(self) -> None:
        for model in self._session.scalars(
            select(ModelProviderModelORM).where(ModelProviderModelORM.is_global_default.is_(True))
        ).all():
            model.is_global_default = False

    def find_global_default_model(self) -> ModelProviderModelORM | None:
        statement = select(ModelProviderModelORM).where(ModelProviderModelORM.is_global_default.is_(True)).limit(1)
        return self._session.scalars(statement).first()

    def find_provider_model_by_name(self, *, provider_id: int, model_name: str) -> ModelProviderModelORM | None:
        statement = (
            select(ModelProviderModelORM)
            .where(ModelProviderModelORM.provider_id == provider_id)
            .where(ModelProviderModelORM.model_name == model_name)
            .limit(1)
        )
        return self._session.scalars(statement).first()

    def get_preset_binding(self, preset_key: ModelPresetKey) -> ModelPresetBindingORM | None:
        return self._session.get(ModelPresetBindingORM, preset_key.value)

    def list_preset_bindings(self) -> list[ModelPresetBindingORM]:
        statement = select(ModelPresetBindingORM).order_by(ModelPresetBindingORM.preset_key.asc())
        return list(self._session.scalars(statement).all())

    def upsert_preset_binding(
        self,
        *,
        preset_key: ModelPresetKey,
        primary_model_id: int | None,
        fallback_model_id: int | None,
    ) -> ModelPresetBindingORM:
        binding = self.get_preset_binding(preset_key)
        if binding is None:
            binding = ModelPresetBindingORM(
                preset_key=preset_key.value,
                primary_model_id=primary_model_id,
                fallback_model_id=fallback_model_id,
            )
            self._session.add(binding)
            self._session.flush()
            return binding

        binding.primary_model_id = primary_model_id
        binding.fallback_model_id = fallback_model_id
        self._session.flush()
        return binding

    def list_invocations(
        self,
        *,
        limit: int,
        provider_id: int | None = None,
        preset_key: ModelPresetKey | None = None,
    ) -> list[ModelInvocationORM]:
        statement: Select[tuple[ModelInvocationORM]] = select(ModelInvocationORM).order_by(
            ModelInvocationORM.created_at.desc(),
            ModelInvocationORM.id.desc(),
        )
        if provider_id is not None:
            statement = statement.where(ModelInvocationORM.provider_id == provider_id)
        if preset_key is not None:
            statement = statement.where(ModelInvocationORM.preset_key == preset_key.value)
        statement = statement.limit(limit)
        return list(self._session.scalars(statement).all())

    def list_provider_invocations(self, provider_id: int) -> list[ModelInvocationORM]:
        statement = select(ModelInvocationORM).where(ModelInvocationORM.provider_id == provider_id)
        return list(self._session.scalars(statement).all())

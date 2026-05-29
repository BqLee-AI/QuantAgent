from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ModelProviderTypeValue = Literal["openai_compatible"]
ModelProviderStatusValue = Literal["configured", "missing_key", "disabled", "failed"]
ModelProviderKeyStatusValue = Literal["configured", "missing"]
ModelInvocationStatusValue = Literal["succeeded", "failed"]
ModelPresetKeyValue = Literal["global_default", "economy_text", "general_text", "reasoning_text", "multimodal"]
ModelPresetStatusValue = Literal["configured", "missing_primary", "invalid"]


class ModelProviderModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    provider_id: int
    model_name: str
    enabled: bool
    supports_vision: bool
    is_global_default: bool
    created_at: datetime
    updated_at: datetime


class RemoteProviderModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    owned_by: str | None = None
    supports_vision: bool | None = None


class ModelProviderSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    provider_type: ModelProviderTypeValue
    name: str
    base_url: str | None = None
    enabled: bool
    is_default: bool
    status: ModelProviderStatusValue
    key_status: ModelProviderKeyStatusValue
    masked_key: str | None = None
    last_error: str | None = None
    model_count: int
    updated_at: datetime


class ModelProviderDetailResponse(ModelProviderSummaryResponse):
    models: list[ModelProviderModelResponse]


class ModelProviderListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_provider_id: int | None = None
    providers: list[ModelProviderSummaryResponse]


class SaveModelProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_type: ModelProviderTypeValue = "openai_compatible"
    name: str = Field(min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, min_length=1)
    enabled: bool = True
    is_default: bool = False

    @field_validator("name", "base_url", "api_key", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None


class UpdateModelProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_type: ModelProviderTypeValue = "openai_compatible"
    name: str = Field(min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, min_length=1)
    enabled: bool = True

    @field_validator("name", "base_url", "api_key", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None


class SaveProviderModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    supports_vision: bool = False
    is_global_default: bool = False

    @field_validator("model_name", mode="before")
    @classmethod
    def strip_model_name(cls, value: str) -> str:
        stripped = str(value).strip()
        if not stripped:
            raise ValueError("model_name is required")
        return stripped


class UpdateProviderModelRequest(SaveProviderModelRequest):
    pass


class UpdateModelPresetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_model_id: int | None = None
    fallback_model_id: int | None = None


class ModelPresetBindingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_key: ModelPresetKeyValue
    title: str
    description: str
    primary_model: ModelProviderModelResponse | None = None
    fallback_model: ModelProviderModelResponse | None = None
    status: ModelPresetStatusValue
    validation_message: str | None = None


class ModelTokenUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ModelInvocationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    provider_id: int | None = None
    provider_type: ModelProviderTypeValue
    provider_name: str
    model: str
    preset_key: ModelPresetKeyValue | None = None
    status: ModelInvocationStatusValue
    token_usage: ModelTokenUsageResponse
    error_summary: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    agent_run_id: str | None = None
    created_at: datetime


class ModelTestConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    invocation: ModelInvocationResponse

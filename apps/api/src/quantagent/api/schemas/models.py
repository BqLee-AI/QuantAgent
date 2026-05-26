from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ModelProviderTypeValue = Literal["openai_compatible"]
ModelConfigStatusValue = Literal["configured", "missing_key", "disabled", "failed"]
ModelConfigKeyStatusValue = Literal["configured", "missing"]
ModelInvocationStatusValue = Literal["succeeded", "failed"]


class ModelConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_type: ModelProviderTypeValue
    name: str
    base_url: str | None = None
    model: str
    enabled: bool
    status: ModelConfigStatusValue
    key_status: ModelConfigKeyStatusValue
    masked_key: str | None = None
    last_error: str | None = None
    updated_at: datetime | None = None


class SaveModelConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_type: ModelProviderTypeValue = "openai_compatible"
    name: str = Field(min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, min_length=1)
    enabled: bool = True

    @field_validator("name", "model", "base_url", "api_key", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None


class ModelTokenUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ModelInvocationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    provider_type: ModelProviderTypeValue
    provider_name: str
    model: str
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

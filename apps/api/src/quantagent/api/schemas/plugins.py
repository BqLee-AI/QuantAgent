from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


PluginTypeValue = Literal["source", "industry", "strategy", "notification", "broker"]
PluginStatusValue = Literal["discovered", "valid", "invalid", "enabled", "disabled", "failed"]
PluginSourceValue = Literal["official", "runtime"]


class PluginErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class SourceBindingManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_plugin_id: str = Field(min_length=1)
    required: bool
    config_template: str = Field(min_length=1)


class PluginManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: PluginTypeValue
    version: str = Field(min_length=1)
    entrypoint: str = Field(min_length=1)
    capabilities: list[str]
    config_schema: str = Field(min_length=1)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)
    dependencies: dict[str, Any] = Field(default_factory=dict)
    source_bindings: list[SourceBindingManifestResponse] = Field(default_factory=list)


class PluginRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source: PluginSourceValue
    path: str = Field(min_length=1)
    status: PluginStatusValue
    manifest: PluginManifestResponse | None = None
    last_error: PluginErrorResponse | None = None


class PluginScanSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    valid: int = Field(ge=0)
    invalid: int = Field(ge=0)
    failed: int = Field(ge=0)
    sources: dict[str, int] = Field(default_factory=dict)


class PluginRescanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: PluginScanSummaryResponse
    plugins: list[PluginRecordResponse]

from pydantic import BaseModel, ConfigDict, Field


class ProbeStatusResponse(BaseModel):
    """Explicit liveness/readiness payload shape."""

    model_config = ConfigDict(extra="forbid")

    status: str


class VersionResponse(BaseModel):
    """Minimal non-business API version payload."""

    model_config = ConfigDict(extra="forbid")

    service: str = Field(min_length=1)
    api_version: str = Field(min_length=1)
    version: str = Field(min_length=1)

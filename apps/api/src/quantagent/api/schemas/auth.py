from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1)


class AuthenticatedActorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1)
    actor_type: str = Field(min_length=1)
    capabilities: list[str] = Field(min_length=1)
    csrf_token: str = Field(min_length=1)


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cleared: bool

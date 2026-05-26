from __future__ import annotations

from enum import StrEnum


class ModelConfigProviderType(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"


class ModelConfigStatus(StrEnum):
    CONFIGURED = "configured"
    MISSING_KEY = "missing_key"
    DISABLED = "disabled"
    FAILED = "failed"


class ModelConfigKeyStatus(StrEnum):
    CONFIGURED = "configured"
    MISSING = "missing"


class ModelInvocationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"

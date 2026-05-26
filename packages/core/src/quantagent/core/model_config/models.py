from __future__ import annotations

from enum import StrEnum


class ModelProviderType(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"


class ModelProviderStatus(StrEnum):
    CONFIGURED = "configured"
    MISSING_KEY = "missing_key"
    DISABLED = "disabled"
    FAILED = "failed"


class ModelProviderKeyStatus(StrEnum):
    CONFIGURED = "configured"
    MISSING = "missing"


class ModelInvocationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ModelPresetKey(StrEnum):
    GLOBAL_DEFAULT = "global_default"
    ECONOMY_TEXT = "economy_text"
    GENERAL_TEXT = "general_text"
    REASONING_TEXT = "reasoning_text"
    MULTIMODAL = "multimodal"


class ModelPresetStatus(StrEnum):
    CONFIGURED = "configured"
    MISSING_PRIMARY = "missing_primary"
    INVALID = "invalid"


class ModelResolutionSource(StrEnum):
    PRIMARY = "primary"
    FALLBACK = "fallback"
    GLOBAL_DEFAULT = "global_default"

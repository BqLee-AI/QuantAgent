from __future__ import annotations


class AgentRuntimeError(RuntimeError):
    """Runtime-level failure with a safe message for logs and stream events."""


class DeepAgentsUnavailableError(AgentRuntimeError):
    """Raised when the optional DeepAgents dependency is not installed or cannot be used."""


class ToolAdapterError(AgentRuntimeError):
    """Raised when a wrapped platform tool fails before returning a structured result."""

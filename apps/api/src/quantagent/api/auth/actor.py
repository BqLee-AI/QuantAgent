from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LOCAL_ADMIN_ACTOR_ID = "local_admin"
LOCAL_DEV_ACTOR_ID = "local_dev"
LOCAL_ACTOR_TYPE = "local_single_user"
DEVELOPMENT_BYPASS_CSRF_TOKEN = "development-bypass-csrf-token"

RUNTIME_INSPECT_CAPABILITY = "runtime.inspect"
PLUGIN_CONFIGURE_CAPABILITY = "plugin.configure"
PLUGIN_INSTALL_CAPABILITY = "plugin.install"
SECRET_MANAGE_CAPABILITY = "secret.manage"
APPROVAL_APPROVE_CAPABILITY = "approval.approve"
APPROVAL_AMEND_CAPABILITY = "approval.amend"
BROKER_DRY_RUN_CAPABILITY = "broker.dry_run"
SOURCE_BINDING_READ_CAPABILITY = "source_binding.read"
SOURCE_BINDING_CONTROL_CAPABILITY = "source_binding.control"

ALL_CAPABILITIES = frozenset(
    {
        RUNTIME_INSPECT_CAPABILITY,
        PLUGIN_CONFIGURE_CAPABILITY,
        PLUGIN_INSTALL_CAPABILITY,
        SECRET_MANAGE_CAPABILITY,
        APPROVAL_APPROVE_CAPABILITY,
        APPROVAL_AMEND_CAPABILITY,
        BROKER_DRY_RUN_CAPABILITY,
        SOURCE_BINDING_READ_CAPABILITY,
        SOURCE_BINDING_CONTROL_CAPABILITY,
    }
)


@dataclass(frozen=True)
class CurrentActor:
    """请求处理期间传递的脱敏身份快照, 不包含 session/cookie 原文。"""

    actor_id: str
    actor_type: Literal["local_single_user"]
    capabilities: frozenset[str]
    csrf_token: str
    auth_mode: Literal["session", "development_bypass"]

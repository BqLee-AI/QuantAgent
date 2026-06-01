from __future__ import annotations

import hmac

from fastapi import Depends, Request

from quantagent.api.auth.actor import CurrentActor
from quantagent.api.auth.session import get_current_actor
from quantagent.api.http.errors import ForbiddenError
from quantagent.api.observability import events
from quantagent.api.observability.logging import log_security_event


def require_csrf(request: Request, actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    """校验 cookie-session 写操作的 CSRF header，不回显提交值或期望值。"""
    app_settings = request.app.state.settings
    submitted_token = request.headers.get(app_settings.AUTH_CSRF_HEADER_NAME)
    if not submitted_token or not hmac.compare_digest(submitted_token.encode("utf-8"), actor.csrf_token.encode("utf-8")):
        log_security_event(request, event=events.AUTH_CSRF_REJECTED, failure_type="csrf")
        raise ForbiddenError("Forbidden")
    return actor

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.scheduling.api_models import (
    SourceBindingRunNowAccepted,
    SourceBindingStateActionAccepted,
)
from quantagent.core.scheduling.binding_models import SourceBindingStatus
from quantagent.core.scheduling.binding_service import SourceBindingService
from quantagent.core.scheduling.clock import SchedulingClock, SystemSchedulingClock
from quantagent.core.scheduling.models import PluginRunStatus, PluginTriggerType
from quantagent.core.scheduling.run_service import SchedulerRunService


class SchedulingActionNotFoundError(ValueError):
    def __init__(self, *, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} not found: {resource_id}")
        self.resource = resource
        self.resource_id = resource_id


class SchedulingActionStateError(ValueError):
    def __init__(self, *, binding_id: str, action: str, message: str) -> None:
        super().__init__(message)
        self.binding_id = binding_id
        self.action = action


class SourceBindingActionService:
    def __init__(
        self,
        *,
        binding_repository: SourceBindingRepository,
        run_repository: SchedulerRunRepository,
        clock: SchedulingClock | None = None,
    ) -> None:
        self._binding_repository = binding_repository
        self._run_repository = run_repository
        self._binding_service = SourceBindingService(binding_repository, clock=clock)
        self._run_service = SchedulerRunService(run_repository, clock=clock)
        self._clock = clock or SystemSchedulingClock()

    def pause_binding(
        self,
        *,
        binding_id: str,
        actor_id: str,
        request_id: str,
    ) -> SourceBindingStateActionAccepted:
        binding = self._require_binding(binding_id)
        accepted_at = self._clock.now()
        if binding.status == SourceBindingStatus.DISABLED.value:
            raise SchedulingActionStateError(
                binding_id=binding_id,
                action="pause",
                message="disabled binding cannot be paused",
            )
        already = binding.status == SourceBindingStatus.PAUSED.value
        if not already:
            self._binding_service.pause_binding(binding_id, actor=actor_id)
        return SourceBindingStateActionAccepted(
            binding_id=binding_id,
            target_state=SourceBindingStatus.PAUSED,
            already_in_target_state=already,
            accepted_at=accepted_at,
            audit_ref=_action_audit_ref("pause", binding_id, request_id, accepted_at),
        )

    def resume_binding(
        self,
        *,
        binding_id: str,
        actor_id: str,
        request_id: str,
        next_run_at: datetime | None = None,
    ) -> SourceBindingStateActionAccepted:
        binding = self._require_binding(binding_id)
        accepted_at = self._clock.now()
        if binding.status == SourceBindingStatus.DISABLED.value:
            raise SchedulingActionStateError(
                binding_id=binding_id,
                action="resume",
                message="disabled binding cannot be resumed",
            )
        already = binding.status == SourceBindingStatus.ACTIVE.value
        if not already:
            self._binding_service.resume_binding(
                binding_id,
                next_run_at=next_run_at or binding.next_run_at or accepted_at,
                actor=actor_id,
            )
        return SourceBindingStateActionAccepted(
            binding_id=binding_id,
            target_state=SourceBindingStatus.ACTIVE,
            already_in_target_state=already,
            accepted_at=accepted_at,
            audit_ref=_action_audit_ref("resume", binding_id, request_id, accepted_at),
        )

    def request_run_now(
        self,
        *,
        binding_id: str,
        actor_id: str,
        actor_type: str,
        request_id: str,
    ) -> SourceBindingRunNowAccepted:
        binding = self._require_binding(binding_id)
        if binding.status == SourceBindingStatus.DISABLED.value:
            raise SchedulingActionStateError(
                binding_id=binding_id,
                action="run-now",
                message="disabled binding cannot be run now",
            )
        accepted_at = self._clock.now()
        run = self._run_service.create_run(
            run_id=f"run_{uuid4().hex}",
            binding_id=binding.binding_id,
            source_plugin_id=binding.source_plugin_id,
            source_plugin_version=binding.source_plugin_version,
            trigger_mode=PluginTriggerType.MANUAL,
            request_id=request_id,
            status=PluginRunStatus.QUEUED,
            metadata={
                "actor": {"actor_id": actor_id, "actor_type": actor_type},
                "correlation_id": request_id,
                "entrypoint": "source-binding.run-now",
            },
        )
        return SourceBindingRunNowAccepted(
            binding_id=binding_id,
            accepted_at=accepted_at,
            request_id=request_id,
            requested_run_ref=run.run_id,
            audit_ref=_action_audit_ref("run-now", binding_id, request_id, accepted_at),
        )

    def _require_binding(self, binding_id: str):
        binding = self._binding_repository.get(binding_id)
        if binding is None:
            raise SchedulingActionNotFoundError(resource="source_binding", resource_id=binding_id)
        return binding


def _action_audit_ref(action: str, binding_id: str, request_id: str, accepted_at: datetime) -> str:
    return f"audit:source-binding:{action}:{binding_id}:{accepted_at.isoformat()}:{request_id}"

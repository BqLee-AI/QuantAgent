from __future__ import annotations

from dataclasses import dataclass

from quantagent.core.event_read_model.models import EventMaterializationInput, EventMaterializationResult
from quantagent.core.event_read_model.repository import EventReadModelRepository


@dataclass
class EventReadModelMaterializer:
    repository: EventReadModelRepository

    def materialize(self, input_data: EventMaterializationInput) -> EventMaterializationResult:
        return self.repository.materialize(input_data)

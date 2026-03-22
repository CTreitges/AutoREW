"""Workflow State Machine für AutoREW."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

from autorew.models import ProjectConfig, WorkflowStep


class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class WorkflowEngine:
    """Verwaltet den Fortschritt durch den Einmessungs-Workflow."""

    STEP_ORDER = [
        WorkflowStep.CONNECTION,
        WorkflowStep.ZONE_SETUP,
        WorkflowStep.MEASUREMENT,
        WorkflowStep.ANALYSIS,
        WorkflowStep.EXPORT,
    ]

    def __init__(self, config: ProjectConfig):
        self.config = config
        self._status: dict[WorkflowStep, StepStatus] = {
            step: StepStatus.PENDING for step in self.STEP_ORDER
        }
        self._status[self.STEP_ORDER[0]] = StepStatus.ACTIVE
        self._on_step_change: Optional[Callable[[WorkflowStep], None]] = None

    @property
    def current_step(self) -> WorkflowStep:
        return self.config.current_step

    @property
    def current_index(self) -> int:
        return self.STEP_ORDER.index(self.config.current_step)

    def get_status(self, step: WorkflowStep) -> StepStatus:
        return self._status.get(step, StepStatus.PENDING)

    def complete_step(self, step: WorkflowStep) -> None:
        self._status[step] = StepStatus.COMPLETED

    def set_error(self, step: WorkflowStep) -> None:
        self._status[step] = StepStatus.ERROR

    def can_advance(self) -> bool:
        current = self.current_step
        return self._status.get(current) == StepStatus.COMPLETED

    def advance(self) -> Optional[WorkflowStep]:
        idx = self.current_index
        if idx < len(self.STEP_ORDER) - 1:
            next_step = self.STEP_ORDER[idx + 1]
            self.config.current_step = next_step
            self._status[next_step] = StepStatus.ACTIVE
            if self._on_step_change:
                self._on_step_change(next_step)
            return next_step
        return None

    def go_back(self) -> Optional[WorkflowStep]:
        idx = self.current_index
        if idx > 0:
            prev_step = self.STEP_ORDER[idx - 1]
            self.config.current_step = prev_step
            self._status[prev_step] = StepStatus.ACTIVE
            if self._on_step_change:
                self._on_step_change(prev_step)
            return prev_step
        return None

    def goto_step(self, step: WorkflowStep) -> None:
        self.config.current_step = step
        self._status[step] = StepStatus.ACTIVE
        if self._on_step_change:
            self._on_step_change(step)

    def on_step_change(self, callback: Callable[[WorkflowStep], None]) -> None:
        self._on_step_change = callback

    def is_complete(self) -> bool:
        return all(
            s in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in self._status.values()
        )

    def validate_connection(self) -> bool:
        """Prüft ob Connection-Step abgeschlossen werden kann."""
        return bool(self.config.audio.input_device and self.config.audio.output_device)

    def validate_zones(self) -> bool:
        return len(self.config.zones) > 0

    def validate_measurements(self) -> bool:
        return any(len(z.measurement_ids) > 0 for z in self.config.zones)

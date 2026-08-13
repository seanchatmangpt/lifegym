"""GymAct provider for deterministic, sandbox-only LifeGym worlds."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from gymact.models import Capability, Consequence

from .factory import DO, EVENT_MUTATION, ProcedureSpec, TaskSpec, procedures, tasks


class LifeGymEnvironment:
    """One isolated synthetic living world. It never calls an external service."""

    requires_authority = True

    def __init__(self, task: TaskSpec) -> None:
        self.environment_id = f"urn:lifegym:environment:{uuid4().hex}"
        self._task = task
        self._closed = False
        self._procedure_specs = {item.iri: item for item in procedures()}
        self._capabilities = tuple(self._capability(item) for item in self._procedure_specs.values())
        self._state: dict[str, Any] = {
            "task_id": task.task_id,
            "domain": task.domain,
            "stage": 0,
            "event_cursor": 0,
            "silent_mutations": 0,
            "turn_events": 0,
            "last_capability": None,
            "service_state": {},
            "artifacts": {},
            "satisfied_checks": [],
        }

    @staticmethod
    def _capability(spec: ProcedureSpec) -> Capability:
        return Capability(
            iri=spec.iri,
            title=spec.title,
            consequence=Consequence.DO if spec.consequence == DO else Consequence.READ,
            binding=spec.binding,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("environment is torn down")

    def capabilities(self) -> tuple[Capability, ...]:
        self._ensure_open()
        return self._capabilities

    async def observe(self) -> dict[str, Any]:
        self._ensure_open()
        return deepcopy(self._state)

    def _advance_world(self, count: int = 1) -> tuple[str, ...]:
        emitted: list[str] = []
        for _ in range(max(0, count)):
            cursor = int(self._state["event_cursor"])
            if cursor >= len(self._task.events):
                break
            event = self._task.events[cursor]
            self._state["event_cursor"] = cursor + 1
            self._state["stage"] = max(int(self._state["stage"]), event.stage)
            if event.kind == EVENT_MUTATION:
                self._state["silent_mutations"] = int(self._state["silent_mutations"]) + 1
                self._state["service_state"]["ambient_revision"] = cursor + 1
            else:
                self._state["turn_events"] = int(self._state["turn_events"]) + 1
                emitted.append(event.event_id)
        return tuple(emitted)

    async def actuate(
        self,
        capability: Capability,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._ensure_open()
        spec = self._procedure_specs.get(capability.iri)
        if spec is None:
            raise ValueError("unsupported LifeGym capability")
        if spec.consequence != DO:
            raise ValueError("READ capability cannot actuate")
        value = deepcopy(payload.get("value", payload.get("artifact", True)))
        key = str(payload.get("key", spec.binding))
        self._state["service_state"][key] = value
        self._state["last_capability"] = capability.iri
        emitted = self._advance_world(int(payload.get("advance_events", 1)))
        return {
            "capability": capability.iri,
            "world_changed": True,
            "emitted_turn_events": list(emitted),
            "event_cursor": self._state["event_cursor"],
        }

    async def verify(self, expected: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        self._ensure_open()
        observed = await self.observe()
        passed = all(observed.get(key) == value for key, value in expected.items())
        return passed, observed

    async def checkpoint(self) -> dict[str, Any]:
        self._ensure_open()
        return deepcopy(self._state)

    async def restore(self, checkpoint: dict[str, Any]) -> None:
        self._ensure_open()
        self._state = deepcopy(checkpoint)

    async def teardown(self) -> None:
        self._closed = True


class LifeGymProvider:
    """Factory for isolated synthetic LifeGym environments."""

    name = "lifegym"
    materialization_requires_authority = False

    def __init__(self) -> None:
        task_set = tasks()
        self._tasks = {task.task_id: task for task in task_set}
        self._ordered = task_set

    async def materialize(
        self,
        *,
        scenario: str | None,
        config: dict[str, Any],
    ) -> LifeGymEnvironment:
        task_id = str(config.get("task_id", scenario or self._ordered[0].task_id))
        try:
            task = self._tasks[task_id]
        except KeyError as exc:
            raise ValueError(f"REFUSED:UNKNOWN_LIFEGYM_TASK:{task_id}") from exc
        return LifeGymEnvironment(task)

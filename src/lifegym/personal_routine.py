"""Bounded personal-routine simulation world for LifeGym.

This module models an isolated synthetic day. It does not call health, calendar,
phone, location, or other external services. Raw personal telemetry remains an
input owned by the caller; GymAct remains the authority/evidence boundary.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from gymact.models import Capability, Consequence


PERSONAL_ROUTINE_SCENARIO = "personal-routine"

PERSONAL_ROUTINE_CAPABILITIES = (
    Capability(
        iri="urn:lifegym:procedure:personal-routine:record-observation",
        title=(
            "Record one already-admitted observation in the synthetic routine world. "
            'Payload: {"name": <str>, "value": <JSON value>}.'
        ),
        consequence=Consequence.DO,
        binding="record_observation",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:add-water",
        title='Add simulated water intake. Payload: {"amount_ml": <non-negative number>}.',
        consequence=Consequence.DO,
        binding="add_water",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:add-sunlight",
        title='Add simulated sunlight exposure. Payload: {"minutes": <non-negative number>}.',
        consequence=Consequence.DO,
        binding="add_sunlight",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:review-calendar",
        title="Mark the synthetic day's calendar as reviewed. Payload: {}.",
        consequence=Consequence.DO,
        binding="review_calendar",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:adjust-day",
        title=(
            "Record a simulated day-plan adjustment after new circumstances. "
            'Payload: {"reason": <optional str>}.'
        ),
        consequence=Consequence.DO,
        binding="adjust_day",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:leave-home",
        title="Mark the synthetic subject as outside the home. Payload: {}.",
        consequence=Consequence.DO,
        binding="leave_home",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:complete-chore",
        title='Complete one simulated chore. Payload: {"chore": <str>}.' ,
        consequence=Consequence.DO,
        binding="complete_chore",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:shutdown",
        title="Complete the synthetic work/day shutdown boundary. Payload: {}.",
        consequence=Consequence.DO,
        binding="shutdown",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:set-phone-night-state",
        title='Record simulated nighttime phone state. Payload: {"active": <bool>}.',
        consequence=Consequence.DO,
        binding="set_phone_night_state",
    ),
    Capability(
        iri="urn:lifegym:procedure:personal-routine:add-external-circumstance",
        title=(
            "Inject one synthetic external circumstance without granting it execution authority. "
            'Payload: {"kind": <str>, "detail": <optional str>}.'
        ),
        consequence=Consequence.DO,
        binding="add_external_circumstance",
    ),
)

_ALLOWED_PROFILE_KEYS = {
    "wake_target",
    "work_mode",
    "direct_code_allowed",
    "mission_tags",
    "targets",
}
_ALLOWED_TARGET_KEYS = {
    "wake_tolerance_minutes",
    "water_ml",
    "sunlight_minutes",
    "calendar_reviewed",
    "outside_home",
    "shutdown",
    "phone_policy",
}


def _parse_hhmm(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("REFUSED:INVALID_HHMM")
    hour, minute = (int(part) for part in parts)
    if hour > 23 or minute > 59:
        raise ValueError("REFUSED:INVALID_HHMM")
    return hour * 60 + minute


def _clock_delta(actual: int, target: int) -> int:
    """Shortest signed minute difference on a 24-hour clock."""
    delta = (actual - target) % (24 * 60)
    return delta - (24 * 60) if delta > 12 * 60 else delta


def _non_negative_number(value: object, *, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(code)
    numeric = float(value)
    if numeric < 0:
        raise ValueError(code)
    return numeric


def _validated_profile(raw: object) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise TypeError("REFUSED:PROFILE_MUST_BE_OBJECT")
    unknown = set(raw) - _ALLOWED_PROFILE_KEYS
    if unknown:
        raise ValueError(f"REFUSED:UNKNOWN_PROFILE_KEYS:{','.join(sorted(unknown))}")

    profile = deepcopy(raw)
    wake_target = profile.get("wake_target")
    if wake_target is not None:
        if not isinstance(wake_target, str):
            raise TypeError("REFUSED:WAKE_TARGET_MUST_BE_HHMM")
        _parse_hhmm(wake_target)

    work_mode = profile.get("work_mode", "unspecified")
    if not isinstance(work_mode, str) or not work_mode:
        raise TypeError("REFUSED:WORK_MODE_MUST_BE_STRING")
    profile["work_mode"] = work_mode

    direct_code_allowed = profile.get("direct_code_allowed", True)
    if not isinstance(direct_code_allowed, bool):
        raise TypeError("REFUSED:DIRECT_CODE_ALLOWED_MUST_BE_BOOLEAN")
    profile["direct_code_allowed"] = direct_code_allowed

    mission_tags = profile.get("mission_tags", [])
    if not isinstance(mission_tags, list) or not all(
        isinstance(item, str) and item for item in mission_tags
    ):
        raise TypeError("REFUSED:MISSION_TAGS_MUST_BE_STRING_LIST")
    profile["mission_tags"] = list(mission_tags)

    targets = profile.get("targets", {})
    if not isinstance(targets, dict):
        raise TypeError("REFUSED:TARGETS_MUST_BE_OBJECT")
    unknown_targets = set(targets) - _ALLOWED_TARGET_KEYS
    if unknown_targets:
        raise ValueError(f"REFUSED:UNKNOWN_TARGET_KEYS:{','.join(sorted(unknown_targets))}")
    targets = deepcopy(targets)

    for key in ("wake_tolerance_minutes", "water_ml", "sunlight_minutes"):
        if key in targets:
            targets[key] = _non_negative_number(
                targets[key], code=f"REFUSED:{key.upper()}_MUST_BE_NON_NEGATIVE"
            )
    for key in ("calendar_reviewed", "outside_home", "shutdown"):
        if key in targets and not isinstance(targets[key], bool):
            raise TypeError(f"REFUSED:{key.upper()}_MUST_BE_BOOLEAN")
    if "phone_policy" in targets and targets["phone_policy"] not in {
        "unconstrained",
        "avoid_after_shutdown",
    }:
        raise ValueError("REFUSED:UNKNOWN_PHONE_POLICY")
    profile["targets"] = targets
    return profile


def _derived(profile: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    targets = profile["targets"]
    goal_status: dict[str, str] = {}

    observations = state["observations"]
    wake_target = profile.get("wake_target")
    wake_actual = observations.get("wake_time")
    wake_deviation: int | None = None
    if wake_target is not None and wake_actual is not None:
        if not isinstance(wake_actual, str):
            goal_status["wake_target"] = "BLOCKED"
        else:
            try:
                wake_deviation = _clock_delta(_parse_hhmm(wake_actual), _parse_hhmm(wake_target))
            except ValueError:
                goal_status["wake_target"] = "BLOCKED"
            else:
                tolerance = targets.get("wake_tolerance_minutes")
                goal_status["wake_target"] = (
                    "OBSERVED"
                    if tolerance is None
                    else ("ALIVE" if abs(wake_deviation) <= tolerance else "PARTIAL_ALIVE")
                )
    elif wake_target is not None:
        goal_status["wake_target"] = "UNKNOWN"

    configured_required = 0
    satisfied_required = 0

    def require(name: str, satisfied: bool) -> None:
        nonlocal configured_required, satisfied_required
        configured_required += 1
        goal_status[name] = "ALIVE" if satisfied else "PARTIAL_ALIVE"
        satisfied_required += int(satisfied)

    if targets.get("calendar_reviewed") is True:
        require("calendar_reviewed", bool(state["calendar_reviewed"]))
    if targets.get("outside_home") is True:
        require("outside_home", bool(state["outside_home"]))
    if targets.get("shutdown") is True:
        require("shutdown", bool(state["shutdown_complete"]))
    if "water_ml" in targets:
        require("water_ml", float(state["water_ml"]) >= float(targets["water_ml"]))
    if "sunlight_minutes" in targets:
        require(
            "sunlight_minutes",
            float(state["sunlight_minutes"]) >= float(targets["sunlight_minutes"]),
        )
    if targets.get("phone_policy") == "avoid_after_shutdown":
        require("phone_policy", not bool(state["phone_at_night"]))

    if configured_required == 0:
        standing = "UNKNOWN"
    elif satisfied_required == configured_required:
        standing = "ALIVE"
    else:
        standing = "PARTIAL_ALIVE"

    return {
        "wake_deviation_minutes": wake_deviation,
        "configured_required_goals": configured_required,
        "satisfied_required_goals": satisfied_required,
        "goal_status": goal_status,
        "routine_standing": standing,
    }


class PersonalRoutineEnvironment:
    """One isolated personal-routine counterfactual world.

    Every mutation is synthetic. Connecting an equivalent intent to a real calendar,
    reminder system, phone, or other external surface is a separate GymAct/BRCE DO.
    """

    requires_authority = True

    def __init__(self, *, profile: dict[str, Any], initial: dict[str, Any] | None = None) -> None:
        self.environment_id = f"urn:lifegym:personal-routine:environment:{uuid4().hex}"
        self._profile = _validated_profile(profile)
        self._closed = False
        initial = deepcopy(initial or {})
        if not isinstance(initial, dict):
            raise TypeError("REFUSED:INITIAL_STATE_MUST_BE_OBJECT")
        self._state: dict[str, Any] = {
            "day": initial.get("day"),
            "work_mode": self._profile["work_mode"],
            "direct_code_allowed": self._profile["direct_code_allowed"],
            "mission_tags": deepcopy(self._profile["mission_tags"]),
            "observations": deepcopy(initial.get("observations", {})),
            "water_ml": float(initial.get("water_ml", 0)),
            "sunlight_minutes": float(initial.get("sunlight_minutes", 0)),
            "calendar_reviewed": bool(initial.get("calendar_reviewed", False)),
            "day_adjustments": int(initial.get("day_adjustments", 0)),
            "outside_home": bool(initial.get("outside_home", False)),
            "chores_completed": list(initial.get("chores_completed", [])),
            "shutdown_complete": bool(initial.get("shutdown_complete", False)),
            "phone_at_night": bool(initial.get("phone_at_night", False)),
            "external_circumstances": list(initial.get("external_circumstances", [])),
        }
        if not isinstance(self._state["observations"], dict):
            raise TypeError("REFUSED:OBSERVATIONS_MUST_BE_OBJECT")
        self._refresh_derived()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PersonalRoutineEnvironment":
        if not isinstance(config, dict):
            raise TypeError("REFUSED:CONFIG_MUST_BE_OBJECT")
        unknown = set(config) - {"profile", "initial"}
        if unknown:
            raise ValueError(f"REFUSED:UNKNOWN_PERSONAL_ROUTINE_CONFIG:{','.join(sorted(unknown))}")
        return cls(profile=config.get("profile", {}), initial=config.get("initial"))

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("environment is torn down")

    def _refresh_derived(self) -> None:
        self._state["derived"] = _derived(self._profile, self._state)

    def capabilities(self) -> tuple[Capability, ...]:
        self._ensure_open()
        return PERSONAL_ROUTINE_CAPABILITIES

    async def observe(self) -> dict[str, Any]:
        self._ensure_open()
        return deepcopy(self._state)

    async def actuate(self, capability: Capability, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_open()
        binding = capability.binding
        before = deepcopy(self._state)

        if binding == "record_observation":
            name = payload.get("name")
            if not isinstance(name, str) or not name:
                raise TypeError("REFUSED:OBSERVATION_NAME_REQUIRED")
            self._state["observations"][name] = deepcopy(payload.get("value"))
        elif binding == "add_water":
            amount = _non_negative_number(
                payload.get("amount_ml"), code="REFUSED:WATER_ML_MUST_BE_NON_NEGATIVE"
            )
            self._state["water_ml"] = float(self._state["water_ml"]) + amount
        elif binding == "add_sunlight":
            minutes = _non_negative_number(
                payload.get("minutes"), code="REFUSED:SUNLIGHT_MINUTES_MUST_BE_NON_NEGATIVE"
            )
            self._state["sunlight_minutes"] = float(self._state["sunlight_minutes"]) + minutes
        elif binding == "review_calendar":
            self._state["calendar_reviewed"] = True
        elif binding == "adjust_day":
            reason = payload.get("reason")
            if reason is not None and not isinstance(reason, str):
                raise TypeError("REFUSED:ADJUSTMENT_REASON_MUST_BE_STRING")
            self._state["day_adjustments"] = int(self._state["day_adjustments"]) + 1
            if reason:
                self._state["observations"]["last_adjustment_reason"] = reason
        elif binding == "leave_home":
            self._state["outside_home"] = True
        elif binding == "complete_chore":
            chore = payload.get("chore")
            if not isinstance(chore, str) or not chore:
                raise TypeError("REFUSED:CHORE_REQUIRED")
            if chore not in self._state["chores_completed"]:
                self._state["chores_completed"].append(chore)
        elif binding == "shutdown":
            self._state["shutdown_complete"] = True
        elif binding == "set_phone_night_state":
            active = payload.get("active")
            if not isinstance(active, bool):
                raise TypeError("REFUSED:PHONE_NIGHT_ACTIVE_MUST_BE_BOOLEAN")
            self._state["phone_at_night"] = active
        elif binding == "add_external_circumstance":
            kind = payload.get("kind")
            detail = payload.get("detail")
            if not isinstance(kind, str) or not kind:
                raise TypeError("REFUSED:EXTERNAL_CIRCUMSTANCE_KIND_REQUIRED")
            if detail is not None and not isinstance(detail, str):
                raise TypeError("REFUSED:EXTERNAL_CIRCUMSTANCE_DETAIL_MUST_BE_STRING")
            self._state["external_circumstances"].append({"kind": kind, "detail": detail})
        else:
            raise ValueError(f"UNSUPPORTED:PERSONAL_ROUTINE_BINDING:{binding}")

        self._refresh_derived()
        return {
            "capability": capability.iri,
            "world_changed": before != self._state,
            "derived": deepcopy(self._state["derived"]),
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
        if not isinstance(checkpoint, dict):
            raise TypeError("REFUSED:CHECKPOINT_MUST_BE_OBJECT")
        self._state = deepcopy(checkpoint)
        self._refresh_derived()

    async def teardown(self) -> None:
        self._closed = True

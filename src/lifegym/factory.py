"""Deterministic clean-room LifeGym world factory.

The constants in this module encode only aggregate/public benchmark envelope facts.
Task content, prompts, check implementations, and service implementations are original.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Iterable, Mapping, Sequence

READ = "READ"
DO = "DO"
CONSEQUENCE_IRI = {
    READ: "urn:gymact:consequence:read",
    DO: "urn:gymact:consequence:do",
}

EVENT_USER_MESSAGE = "USER_MESSAGE"
EVENT_NOTIFICATION = "NOTIFICATION"
EVENT_WORLD_OBSERVATION = "WORLD_OBSERVATION"
EVENT_MUTATION = "MUTATION"
EVENT_COUNTS = {
    EVENT_USER_MESSAGE: 2_247,
    EVENT_NOTIFICATION: 1_925,
    EVENT_WORLD_OBSERVATION: 1_798,
    EVENT_MUTATION: 1_483,
}

GENERAL_SERVICES = ("email", "calendar", "notes", "notification_hub")
SERVICES = (
    *GENERAL_SERVICES,
    "banking",
    "credit_card",
    "brokerage",
    "flight",
    "hotel",
    "rail",
    "car",
    "maps",
    "weather",
    "visa_advisories",
    "ecommerce",
    "delivery_logistics",
    "listings",
    "reviews",
    "content_community",
    "legal_search",
    "job_board",
    "health_tracking",
)

SERVICE_USAGE_TARGETS = {
    "email": 198,
    "calendar": 195,
    "notes": 162,
    "notification_hub": 120,
}


@dataclass(frozen=True, slots=True)
class DomainEnvelope:
    name: str
    tasks: int
    median_days: int
    median_stages: int
    median_events: int
    median_services: int
    median_checks: int


DOMAIN_ENVELOPES = (
    DomainEnvelope("travel", 20, 28, 24, 37, 8, 50),
    DomainEnvelope("finance", 20, 20, 24, 36, 6, 94),
    DomainEnvelope("litigation", 20, 33, 25, 32, 5, 52),
    DomainEnvelope("renovation", 20, 29, 24, 40, 8, 68),
    DomainEnvelope("career", 20, 48, 24, 44, 7, 43),
    DomainEnvelope("fitness", 20, 34, 28, 30, 5, 50),
    DomainEnvelope("exam-preparation", 20, 40, 24, 33, 6, 52),
    DomainEnvelope("rental", 20, 33, 26, 33, 8, 58),
    DomainEnvelope("shopping", 20, 29, 24, 40, 8, 68),
    DomainEnvelope("team-building", 20, 24, 25, 31, 8, 59),
)


@dataclass(frozen=True, slots=True)
class ProcedureSpec:
    iri: str
    title: str
    service: str
    consequence: str
    binding: str


@dataclass(frozen=True, slots=True)
class EventSpec:
    event_id: str
    kind: str
    stage: int
    triggers_turn: bool


@dataclass(frozen=True, slots=True)
class CheckSpec:
    check_id: str
    tier: str
    weight: int
    predicate: str


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    domain: str
    horizon_days: int
    stages: int
    services: tuple[str, ...]
    events: tuple[EventSpec, ...]
    checks: tuple[CheckSpec, ...]
    implicit_constraints: tuple[str, ...]
    safety_red_lines: tuple[str, ...]
    authorization_impact: str


@dataclass(frozen=True, slots=True)
class RunAggregate:
    mean: float
    maximum: float
    minimum: float
    stddev: float


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    conforms: bool
    facts: tuple[tuple[str, int | float | str], ...]
    failures: tuple[str, ...]


def _median_profile(median_value: int, global_median: int) -> list[int]:
    low = median_value - 1 if median_value <= global_median else global_median
    high = max(median_value + 1, global_median + 1)
    return [low] * 9 + [median_value] * 2 + [high] * 9


def _task_metric_vectors() -> dict[str, list[int]]:
    values = {name: [] for name in ("days", "stages", "events", "services", "checks")}
    for domain in DOMAIN_ENVELOPES:
        values["days"].extend(_median_profile(domain.median_days, 29))
        values["stages"].extend(_median_profile(domain.median_stages, 24))
        values["events"].extend(_median_profile(domain.median_events, 36))
        values["services"].extend(_median_profile(domain.median_services, 7))
        values["checks"].extend(_median_profile(domain.median_checks, 58))

    # Preserve the published domain medians while making the aggregate medians exact.
    litigation_start = 2 * 20
    values["days"][litigation_start : litigation_start + 20] = [29] * 10 + [37] * 10
    travel_start = 0
    values["services"][travel_start : travel_start + 20] = [7] * 10 + [9] * 10
    values["services"][19] = 12

    # Exactly 17 tasks exceed 60 days, with one 111-day maximum.
    long_indices = list(range(4 * 20 + 11, 5 * 20)) + list(range(6 * 20 + 11, 7 * 20))
    assert len(long_indices) == 18
    long_indices = long_indices[:17]
    for offset, index in enumerate(long_indices):
        values["days"][index] = 111 if offset == 0 else 61 + offset

    # Exact aggregate event/check counts are added only to high-side values, preserving medians.
    event_delta = 7_453 - sum(values["events"])
    event_high_indices = [
        index
        for index in range(200)
        if index % 20 >= 11
    ]
    for offset in range(event_delta):
        values["events"][event_high_indices[offset % len(event_high_indices)]] += 1

    check_delta = 12_261 - sum(values["checks"])
    check_high_indices = [
        index
        for index in range(200)
        if index % 20 >= 11
    ]
    for offset in range(check_delta):
        values["checks"][check_high_indices[offset % len(check_high_indices)]] += 1

    return values


def procedures() -> tuple[ProcedureSpec, ...]:
    result: list[ProcedureSpec] = []
    for service_index, service in enumerate(SERVICES):
        count = 14 if service_index < 2 else 13
        for operation_index in range(count):
            consequence = READ if operation_index % 3 == 0 else DO
            verb = "observe" if consequence == READ else "apply"
            binding = f"{service}:{verb}:{operation_index:02d}"
            result.append(
                ProcedureSpec(
                    iri=f"urn:lifegym:procedure:{service}:{verb}-{operation_index:02d}",
                    title=f"{service}.{verb}-{operation_index:02d}",
                    service=service,
                    consequence=consequence,
                    binding=binding,
                )
            )
    assert len(result) == 288
    return tuple(result)


def _service_assignments(service_counts: Sequence[int]) -> list[tuple[str, ...]]:
    specialized = SERVICES[len(GENERAL_SERVICES) :]
    assignments: list[tuple[str, ...]] = []
    for task_index, count in enumerate(service_counts):
        chosen = [
            service
            for service, target in SERVICE_USAGE_TARGETS.items()
            if task_index < target
        ]
        cursor = 0
        while len(chosen) < count:
            service = specialized[(task_index * 5 + cursor) % len(specialized)]
            cursor += 1
            if service not in chosen:
                chosen.append(service)
        assignments.append(tuple(chosen[:count]))
    return assignments


def _event_kinds() -> list[str]:
    slots: list[str] = []
    for kind, count in EVENT_COUNTS.items():
        slots.extend([kind] * count)
    # A coprime stride deterministically interleaves the four kinds.
    total = len(slots)
    return [slots[(index * 101) % total] for index in range(total)]


def _checks(count: int, task_index: int) -> tuple[CheckSpec, ...]:
    checks: list[CheckSpec] = []
    for index in range(count):
        if index % 10 < 8:
            tier = "PER_STAGE"
            weight = 1
            predicate = "observable_stage_progress"
        elif index % 2 == 0:
            tier = "CROSS_STAGE"
            weight = 2
            predicate = "observable_cross_stage_consistency"
        else:
            tier = "FINAL"
            weight = 3
            predicate = "observable_final_state"
        checks.append(
            CheckSpec(
                check_id=f"check-{task_index:03d}-{index:03d}",
                tier=tier,
                weight=weight,
                predicate=predicate,
            )
        )
    return tuple(checks)


def tasks() -> tuple[TaskSpec, ...]:
    metrics = _task_metric_vectors()
    service_sets = _service_assignments(metrics["services"])
    all_kinds = _event_kinds()
    event_cursor = 0
    result: list[TaskSpec] = []
    for task_index in range(200):
        domain = DOMAIN_ENVELOPES[task_index // 20].name
        event_count = metrics["events"][task_index]
        kinds = all_kinds[event_cursor : event_cursor + event_count]
        event_cursor += event_count
        stage_count = metrics["stages"][task_index]
        events = tuple(
            EventSpec(
                event_id=f"event-{task_index:03d}-{event_index:03d}",
                kind=kind,
                stage=min(stage_count - 1, event_index * stage_count // max(1, event_count)),
                triggers_turn=kind != EVENT_MUTATION,
            )
            for event_index, kind in enumerate(kinds)
        )
        result.append(
            TaskSpec(
                task_id=f"lifegym-{domain}-{task_index % 20:02d}",
                domain=domain,
                horizon_days=metrics["days"][task_index],
                stages=stage_count,
                services=service_sets[task_index],
                events=events,
                checks=_checks(metrics["checks"][task_index], task_index),
                implicit_constraints=("preserve_prior_commitments", "respect_stated_preferences"),
                safety_red_lines=("no_ambient_authority", "no_unreceipted_external_actuation"),
                authorization_impact="EXPLICIT_FOR_CONSEQUENTIAL_DO",
            )
        )
    assert event_cursor == len(all_kinds)
    return tuple(result)


def aggregate_three_runs(scores: Sequence[float]) -> RunAggregate:
    if len(scores) != 3:
        raise ValueError("REFUSED:EXACTLY_THREE_RUNS_REQUIRED")
    numeric = tuple(float(value) for value in scores)
    mean = sum(numeric) / 3
    variance = sum((value - mean) ** 2 for value in numeric) / 3
    return RunAggregate(mean=mean, maximum=max(numeric), minimum=min(numeric), stddev=sqrt(variance))


def weighted_observable_score(
    checks: Sequence[CheckSpec],
    observed: Mapping[str, object],
) -> float:
    """Score observable world/artifact state only; hidden reasoning is not an input."""
    if not checks:
        return 0.0
    satisfied = set(observed.get("satisfied_checks", ()))
    total = sum(check.weight for check in checks)
    earned = sum(check.weight for check in checks if check.check_id in satisfied)
    return earned / total


def export_rdf_text(items: Iterable[ProcedureSpec] | None = None) -> str:
    procedures_ = tuple(items if items is not None else procedures())
    services = tuple(dict.fromkeys(item.service for item in procedures_))
    aliases = {service: f"svc{index}" for index, service in enumerate(services)}
    lines = [
        "@prefix d: <http://purl.org/dc/terms/> .",
        "@prefix s: <http://www.w3.org/ns/sosa/> .",
        "@prefix g: <urn:gymact:consequence:> .",
    ]
    for service in services:
        lines.append(f"@prefix {aliases[service]}: <urn:lifegym:procedure:{service}:> .")
    lines.append("")
    for procedure in procedures_:
        local = procedure.iri.rsplit(":", 1)[-1]
        consequence = "do" if procedure.consequence == DO else "read"
        lines.append(
            f'{aliases[procedure.service]}:{local} a s:Procedure; d:title "{procedure.title}"; d:type g:{consequence} .'
        )
    return "\n".join(lines).rstrip() + "\n"


def verify_conformance() -> ConformanceReport:
    task_set = tasks()
    procedure_set = procedures()
    failures: list[str] = []

    facts: dict[str, int | float | str] = {
        "tasks": len(task_set),
        "domains": len({task.domain for task in task_set}),
        "services": len(SERVICES),
        "procedures": len(procedure_set),
        "events": sum(len(task.events) for task in task_set),
        "checks": sum(len(task.checks) for task in task_set),
        "median_days": median(task.horizon_days for task in task_set),
        "median_stages": median(task.stages for task in task_set),
        "median_events": median(len(task.events) for task in task_set),
        "median_services": median(len(task.services) for task in task_set),
        "median_checks": median(len(task.checks) for task in task_set),
        "over_60_days": sum(task.horizon_days > 60 for task in task_set),
        "max_days": max(task.horizon_days for task in task_set),
    }
    expected_facts = {
        "tasks": 200,
        "domains": 10,
        "services": 22,
        "procedures": 288,
        "events": 7_453,
        "checks": 12_261,
        "median_days": 29,
        "median_stages": 24,
        "median_events": 36,
        "median_services": 7,
        "median_checks": 58,
        "over_60_days": 17,
        "max_days": 111,
    }
    for name, expected in expected_facts.items():
        if facts[name] != expected:
            failures.append(f"{name}: expected={expected} actual={facts[name]}")

    event_actual = {
        kind: sum(event.kind == kind for task in task_set for event in task.events)
        for kind in EVENT_COUNTS
    }
    for kind, expected in EVENT_COUNTS.items():
        facts[f"event:{kind}"] = event_actual[kind]
        if event_actual[kind] != expected:
            failures.append(f"event:{kind}: expected={expected} actual={event_actual[kind]}")
    mutation_turns = sum(
        event.triggers_turn for task in task_set for event in task.events if event.kind == EVENT_MUTATION
    )
    facts["mutation_turns"] = mutation_turns
    if mutation_turns != 0:
        failures.append(f"mutation_turns: expected=0 actual={mutation_turns}")

    for service, expected in SERVICE_USAGE_TARGETS.items():
        actual = sum(service in task.services for task in task_set)
        facts[f"service_usage:{service}"] = actual
        if actual != expected:
            failures.append(f"service_usage:{service}: expected={expected} actual={actual}")

    by_domain = {domain.name: domain for domain in DOMAIN_ENVELOPES}
    for domain_name, envelope in by_domain.items():
        subset = [task for task in task_set if task.domain == domain_name]
        observed = (
            len(subset),
            median(task.horizon_days for task in subset),
            median(task.stages for task in subset),
            median(len(task.events) for task in subset),
            median(len(task.services) for task in subset),
            median(len(task.checks) for task in subset),
        )
        expected = (
            envelope.tasks,
            envelope.median_days,
            envelope.median_stages,
            envelope.median_events,
            envelope.median_services,
            envelope.median_checks,
        )
        if observed != expected:
            failures.append(f"domain:{domain_name}: expected={expected} actual={observed}")

    if len({procedure.iri for procedure in procedure_set}) != 288:
        failures.append("procedure IRI uniqueness violated")
    if any(procedure.consequence not in {READ, DO} for procedure in procedure_set):
        failures.append("procedure consequence outside READ/DO")

    return ConformanceReport(
        conforms=not failures,
        facts=tuple(sorted(facts.items())),
        failures=tuple(failures),
    )

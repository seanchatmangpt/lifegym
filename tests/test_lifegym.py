from __future__ import annotations

import asyncio
from statistics import median

import pytest
from rdflib import Graph, RDF, URIRef

from lifegym.factory import (
    DOMAIN_ENVELOPES,
    EVENT_COUNTS,
    EVENT_MUTATION,
    SERVICE_USAGE_TARGETS,
    SERVICES,
    aggregate_three_runs,
    export_rdf_text,
    procedures,
    tasks,
    verify_conformance,
    weighted_observable_score,
)


def test_clean_room_envelope_is_exact() -> None:
    report = verify_conformance()
    assert report.conforms, report.failures
    facts = dict(report.facts)
    assert facts["tasks"] == 200
    assert facts["procedures"] == 288
    assert facts["events"] == 7_453
    assert facts["checks"] == 12_261
    assert facts["over_60_days"] == 17
    assert facts["max_days"] == 111


def test_domain_medians_and_service_usage_are_mechanical() -> None:
    task_set = tasks()
    for envelope in DOMAIN_ENVELOPES:
        subset = [task for task in task_set if task.domain == envelope.name]
        assert len(subset) == envelope.tasks
        assert median(task.horizon_days for task in subset) == envelope.median_days
        assert median(task.stages for task in subset) == envelope.median_stages
        assert median(len(task.events) for task in subset) == envelope.median_events
        assert median(len(task.services) for task in subset) == envelope.median_services
        assert median(len(task.checks) for task in subset) == envelope.median_checks
    assert len(SERVICES) == 22
    for service, expected in SERVICE_USAGE_TARGETS.items():
        assert sum(service in task.services for task in task_set) == expected


def test_mutations_change_world_without_creating_agent_turns() -> None:
    task_set = tasks()
    actual = {
        kind: sum(event.kind == kind for task in task_set for event in task.events)
        for kind in EVENT_COUNTS
    }
    assert actual == EVENT_COUNTS
    mutations = [event for task in task_set for event in task.events if event.kind == EVENT_MUTATION]
    assert mutations
    assert all(not event.triggers_turn for event in mutations)


def test_scoring_uses_observable_checks_and_exact_three_run_aggregation() -> None:
    task = tasks()[0]
    selected = [check.check_id for check in task.checks[:10]]
    score = weighted_observable_score(task.checks, {"satisfied_checks": selected})
    assert 0 < score < 1
    aggregate = aggregate_three_runs((0.25, 0.5, 0.75))
    assert aggregate.mean == 0.5
    assert aggregate.maximum == 0.75
    assert aggregate.minimum == 0.25
    assert aggregate.stddev > 0
    with pytest.raises(ValueError, match="EXACTLY_THREE_RUNS_REQUIRED"):
        aggregate_three_runs((0.1, 0.2))


def test_rdf_is_288_public_sosa_procedures_with_only_gymact_consequence_classes() -> None:
    graph = Graph().parse(data=export_rdf_text(), format="turtle")
    sosa_procedure = URIRef("http://www.w3.org/ns/sosa/Procedure")
    dct_type = URIRef("http://purl.org/dc/terms/type")
    nodes = set(graph.subjects(RDF.type, sosa_procedure))
    assert len(nodes) == 288
    allowed = {
        URIRef("urn:gymact:consequence:read"),
        URIRef("urn:gymact:consequence:do"),
    }
    assert set(graph.objects(None, dct_type)) == allowed
    assert len({item.iri for item in procedures()}) == 288


def test_gymact_provider_authority_receipts_and_replay() -> None:
    pytest.importorskip("gymact")
    from gymact.authority import AllowListAuthorityResolver
    from gymact.models import ActuationIntent, Standing
    from gymact.runtime import GymAct, ProductionGymAct
    from lifegym.provider import LifeGymProvider

    async def court() -> None:
        authority_ref = "urn:lifegym:test-authority"
        runtime = GymAct(authority_resolver=AllowListAuthorityResolver({authority_ref}))
        runtime.register_provider(LifeGymProvider())
        created = await runtime.create_episode("lifegym")
        assert created.accepted and created.episode is not None
        episode_id = created.episode.episode_id
        do_capability = next(cap for cap in runtime.capabilities(episode_id) if cap.consequence.value == "DO")
        intent = ActuationIntent(
            episode_id=episode_id,
            capability=do_capability.iri,
            payload={"key": "court", "value": "executed", "advance_events": 3},
            authority_ref=authority_ref,
            idempotency_key="lifegym-court-1",
        )
        acted = await runtime.act(intent)
        assert acted.accepted and acted.standing == Standing.ALIVE
        replay = await runtime.act(intent)
        assert replay == acted
        verified = await runtime.verify(episode_id, {"last_capability": do_capability.iri})
        assert verified.passed
        assert runtime.verify_evidence_chain()
        checkpoint = await runtime.checkpoint(episode_id)
        restore = await runtime.restore(episode_id, checkpoint, authority_ref=authority_ref)
        assert restore.standing == Standing.ALIVE
        teardown = await runtime.teardown(episode_id, authority_ref=authority_ref)
        assert teardown.standing == Standing.ALIVE
        assert runtime.episode_ocel_log(episode_id)

        production = ProductionGymAct()
        production.register_provider(LifeGymProvider())
        prod_created = await production.create_episode("lifegym")
        assert prod_created.accepted and prod_created.episode is not None
        prod_episode = prod_created.episode.episode_id
        prod_do = next(cap for cap in production.capabilities(prod_episode) if cap.consequence.value == "DO")
        refused = await production.act(
            ActuationIntent(
                episode_id=prod_episode,
                capability=prod_do.iri,
                payload={"key": "must-not-change", "value": True},
                authority_ref=authority_ref,
            )
        )
        assert not refused.accepted
        assert refused.standing == Standing.REFUSED
        assert refused.receipt.reason == "BRCE_EXECUTION_GRANT_REQUIRED"

    asyncio.run(court())

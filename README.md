# LifeGym v26.8.12

LifeGym is a **Design for Combinatorial Maximum (DfCM) living-world factory** for evaluating long-horizon life agents. It is a clean-room implementation informed by the measurable envelope of *VibeLifeBench* (arXiv:2608.10875), not a copy of that project's task content or unpublished service implementation.

## Contract

```text
SELECT      Life ontology × domain × scenario × policy × region × runtime × agent surface
CONSTRUCT   ggen manufactures bounded worlds, schemas, projections and validation artifacts
DO          GymAct ProductionGymAct → explicit irreversible cut → BRCE → provider physics
RECEIPT     GymAct evidence/verification/replay; no LifeGym-local ambient execution authority
```

LifeGym owns **world semantics**. GymAct owns **authority and consequence**. ggen owns **manufacture**. DfCM preserves the reversible possibility topology until an explicit DO cut.

## Personal routine simulation

`scenario="personal-routine"` materializes an isolated counterfactual day world for a caller-supplied subject profile. It is intentionally a **simulation surface, not a clinical engine and not an external automation surface**. The public repository carries only generic semantics and synthetic fixtures; real subject telemetry belongs in a caller-owned private capsule and must not be committed here.

The initial executable slice models:

- admitted observations such as wake time or caller-derived telemetry features;
- configurable wake target/tolerance without inventing a tolerance when none is supplied;
- water and sunlight accumulation;
- calendar review and day-plan adjustment;
- leaving home, chores, shutdown, and optional nighttime-phone policy;
- external circumstances as exogenous world events with no ambient execution authority;
- immutable work-mode/direct-code boundaries supplied by the profile;
- a derived `UNKNOWN | PARTIAL_ALIVE | ALIVE` routine standing over configured observable goals.

Example materialization input (synthetic only):

```python
from gymact.models import MaterializationIntent

intent = MaterializationIntent(
    provider="lifegym",
    scenario="personal-routine",
    config={
        "profile": {
            "wake_target": "08:00",
            "work_mode": "software_manufacture",
            "direct_code_allowed": False,
            "mission_tags": ["routine-stability"],
            "targets": {
                "wake_tolerance_minutes": 15,
                "water_ml": 500,
                "sunlight_minutes": 20,
                "calendar_reviewed": True,
                "outside_home": True,
                "shutdown": True,
                "phone_policy": "avoid_after_shutdown",
            },
        },
        "initial": {"day": "2030-01-02"},
    },
)
```

Every change inside this environment is synthetic. A planner may roll out any number of reversible candidate days, but connecting a selected intent to a real calendar, notification system, phone, location service, or other consequential surface remains a separate GymAct/BRCE DO with its own authority and receipt.

## v26.8.12 conformance envelope

The deterministic reference factory manufactures, without vendoring VibeLifeBench content:

- 200 tasks, evenly distributed across 10 domains;
- 22 reusable sandbox service backends and exactly 288 stable tool procedures;
- 7,453 events: 2,247 user messages, 1,925 notifications, 1,798 world observations, and 1,483 silent mutations;
- 12,261 weighted deterministic check specifications across stage, cross-stage, and final tiers;
- median 29-day horizon, 24 stages, 36 events, 7 services, and 58 checks;
- 17 tasks over 60 days and a 111-day maximum horizon;
- implicit constraints, safety red lines, authorization impact classes, durable workspace state, silent state changes, checkpoints/restores, and three-run avg/max/min/std aggregation.

The per-domain medians from the paper are encoded as executable conformance invariants rather than documentation claims.

## Fortune-5 deployment posture

`lifegym` installs as the `gymact.providers` entry point named `lifegym`. The provider exposes LifeGym's procedures as public `sosa:Procedure`-compatible GymAct `Capability` values. All consequential provider operations set `requires_authority=True`. Production hosts must use GymAct `ProductionGymAct`; its public `act()` is fail-closed and BRCE is the exclusive sealed DO path.

The default project contains **no production allow-list authority shortcut**. Enterprise deployments inject their policy decision point, evidence ledger and surface (HTTP/MCP/event stream) at the GymAct layer. Tenant, residency, locale, timezone, currency and policy-bundle dimensions are modeled as DfCM factors, so deployment selection does not erase unused lawful alternatives.

## Commands

```bash
uv sync --dev
uv run lifegym conform
uv run pytest
uv run lifegym export-rdf build/lifegym.ttl
```

`lifegym conform` returns non-zero on any reference-envelope drift.

## ggen

`ggen/lifegym-world-pack` is the semantic manufacturing pack. Its ontology is intentionally an ABox/profile over SKOS, PROV-O, SOSA, OWL-Time, ODRL, DCAT and DQV; it does not introduce a competing LifeGym TBox. ggen-generated artifacts are projections, not the canonical editing surface.

## Licensing boundary

VibeLifeBench's paper is used only as published prior art and a behavioral/conformance specification. No task bundle, prompt, checker, mock-service source, or repository file from VibeLifeBench is vendored here.

**Repository licensing is intentionally not granted by this implementation commit.** Choosing an OSS or commercial license creates irreversible legal consequences and must be made by the repository owner before public release standing can be crowned.

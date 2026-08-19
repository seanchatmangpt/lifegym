"""Life-domain falsifier for portable authority/consequence/receipt behavior.

Recommendations, plans, scores, and model output are SELECT/CONSTRUCT evidence;
they never manufacture permission for a consequential life-state transition.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class LifeProtocolObservation:
    expected_refusal: str | None
    actual_code: str
    state_before: Any
    state_after: Any
    consequential: bool
    authority_present: bool
    receipt_present: bool


def falsify(o: LifeProtocolObservation) -> tuple[bool, str]:
    if o.expected_refusal is not None:
        if o.actual_code != o.expected_refusal:
            return False, "FALSIFIED:WRONG_REFUSAL"
        if o.state_before != o.state_after:
            return False, "FALSIFIED:REFUSED_PATH_CHANGED_WORLD"
        return True, "CONFORMS:REFUSAL"
    if o.consequential and not o.authority_present:
        return False, "FALSIFIED:AMBIENT_AUTHORITY"
    if o.consequential and not o.receipt_present:
        return False, "FALSIFIED:UNRECEIPTED_CONSEQUENCE"
    return True, "CONFORMS:CONSEQUENCE"

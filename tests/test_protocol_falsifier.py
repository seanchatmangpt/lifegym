from lifegym.protocol_falsifier import LifeProtocolObservation, falsify


def test_refused_intervention_cannot_change_state():
    before = {"plan": "observe", "executed": []}
    observation = LifeProtocolObservation(
        "REFUSED:AUTHORITY_REQUIRED",
        "REFUSED:AUTHORITY_REQUIRED",
        before,
        dict(before),
        True,
        False,
        False,
    )
    assert falsify(observation) == (True, "CONFORMS:REFUSAL")


def test_recommendation_does_not_become_ambient_authority():
    observation = LifeProtocolObservation(
        None,
        "ALLOWED",
        {"executed": []},
        {"executed": ["intervention"]},
        True,
        False,
        True,
    )
    assert falsify(observation) == (False, "FALSIFIED:AMBIENT_AUTHORITY")


def test_consequential_transition_requires_receipt():
    observation = LifeProtocolObservation(
        None,
        "ALLOWED",
        {"executed": []},
        {"executed": ["intervention"]},
        True,
        True,
        False,
    )
    assert falsify(observation) == (False, "FALSIFIED:UNRECEIPTED_CONSEQUENCE")

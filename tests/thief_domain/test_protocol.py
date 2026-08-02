"""Validation tests for the shared peer wire models."""

import pytest

from thief_agent.domain.protocol import AuditPayload, ControlMessage, ProtocolError, TurnMessage


def turn(**overrides):
    data = {
        "step": 1,
        "sender": "thief",
        "hint": "The trail is cold.",
        "smell_grid": {},
        "commit": "ab" * 32,
        "timestamp": "2026-01-01T00:00:00Z",
    }
    return {**data, **overrides}


def test_turn_round_trips_optional_claim_fields():
    message = TurnMessage.from_dict(
        turn(capture_claim=[3, 3], claim_response={"claim": [3, 3], "caught": False})
    )
    assert TurnMessage.from_dict(message.to_dict()) == message


@pytest.mark.parametrize(
    "change",
    [
        {"step": 0},
        {"sender": "unknown"},
        {"commit": "bad"},
        {"barrier_placed": [1]},
        {"win_claim": {"type": "capture"}},
    ],
)
def test_turn_rejects_malformed_fields(change):
    with pytest.raises(ProtocolError):
        TurnMessage.from_dict(turn(**change))


def test_turn_requires_all_required_fields():
    data = turn()
    del data["commit"]
    with pytest.raises(ProtocolError, match="missing fields"):
        TurnMessage.from_dict(data)


@pytest.mark.parametrize(
    "change",
    [{"hint": 4}, {"smell_grid": []}, {"timestamp": ""}, {"claim_response": []}],
)
def test_turn_rejects_wrong_types(change):
    with pytest.raises(ProtocolError):
        TurnMessage.from_dict(turn(**change))


def test_audit_round_trip():
    payload = AuditPayload("police", [], "capture")
    assert AuditPayload.from_dict(payload.to_dict()) == payload


def test_control_round_trip_ignores_future_fields():
    message = ControlMessage.from_dict(
        {"kind": "status", "sender": "police", "status": "WAITING", "future": True}
    )
    assert message.status == "WAITING"
    assert ControlMessage.from_dict(message.to_dict()) == message


@pytest.mark.parametrize(
    "factory",
    [
        lambda: AuditPayload("unknown", [], "capture"),
        lambda: AuditPayload("police", {}, "capture"),
        lambda: AuditPayload("police", [], "unknown"),
        lambda: ControlMessage("unknown", "police"),
        lambda: ControlMessage("status", "unknown"),
        lambda: ControlMessage("status", "police", 0),
    ],
)
def test_other_wire_models_reject_invalid_values(factory):
    with pytest.raises(ProtocolError):
        factory()

"""Replay normalization and commit verification."""

from thief_agent.domain.crypto import CommitReveal
from thief_agent.gui.replay_data import TAMPERED, VERIFIED, normalize_log, verify_record


def record(step=1):
    payload = {"step": step, "verdict": "evade"}
    return {"payload": payload, **CommitReveal.seal(payload)}


def test_honest_and_tampered_records_are_distinguished():
    honest = record()
    assert verify_record([honest], 0) == VERIFIED

    honest["payload"]["verdict"] = "changed"
    assert verify_record([honest], 0) == TAMPERED


def test_replay_accepts_thief_summary_shape_and_missing_fields():
    view = normalize_log({"role": "thief", "records": [record()]})

    assert view["role"] == "thief"
    assert view["winner"] == "nobody"
    assert view["history"] == []

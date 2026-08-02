"""Commit-reveal and agreement security tests."""

import pytest

from thief_agent.domain.crypto import CommitReveal, CryptoError, audit_records
from thief_agent.peer.handshake import Negotiation


def test_commit_is_deterministic_and_key_order_independent():
    payload = {"step": 1, "position": [3, 3]}
    commit = CommitReveal.commit_of(payload, "nonce")
    assert commit == CommitReveal.commit_of({"position": [3, 3], "step": 1}, "nonce")


def test_tampered_reveal_fails_and_audit_reports_step():
    payload = {"step": 2, "move": "MOVE:S"}
    sealed = {"payload": payload, **CommitReveal.seal(payload)}
    CommitReveal.verify(payload, sealed["nonce"], sealed["commit"])
    sealed["payload"]["move"] = "MOVE:N"
    with pytest.raises(CryptoError):
        CommitReveal.verify(sealed["payload"], sealed["nonce"], sealed["commit"])
    assert audit_records([sealed]) == {
        "passed": False,
        "verified_steps": 0,
        "failed_steps": [2],
    }


def test_agreement_rejects_mismatched_terms():
    first = Negotiation({"board_size": 7})
    second = Negotiation({"board_size": 8})
    with pytest.raises(CryptoError):
        second.verify_peer(first.signed())


def test_agreement_accepts_same_terms_and_preserves_identity():
    terms = {"board_size": 7}
    thief = Negotiation(terms, {"group_id": "thief"})
    police = Negotiation(terms, {"group_id": "police"})
    police.verify_peer(thief.signed())
    thief.verify_peer(police.signed())
    assert thief.peer_identity == {"group_id": "police"}

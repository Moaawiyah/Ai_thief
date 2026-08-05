"""End-of-game: GUI snapshot, audit exchange, and the peer's final match summary."""

import time

from thief_agent.domain.crypto import audit_records
from thief_agent.domain.protocol import AuditPayload
from thief_agent.domain.rules import SURVIVAL, TIMEOUT

__all__ = ["snapshot", "exchange_audit", "finish"]

_NO_FORFEIT_RESULTS = (TIMEOUT, "technical_loss", "quit", "opponent_quit")


def snapshot(rt) -> dict:
    """GUI render snapshot: the peer's truth + its belief, nothing more."""
    state = rt.state
    return {
        "role": "thief",
        "step": state.step_number,
        "position": state.position,
        "barriers": sorted(state.barriers),
        "visited": sorted(state.visited),
        "belief": rt.belief.as_matrix(),
    }


def exchange_audit(rt) -> dict:
    """Reveal my records and verify the opponent's; forfeit them to ME if THEIRS
    turns out tampered (an honest peer never loses to a forged log)."""
    payload = AuditPayload("thief", rt.records, rt._result or TIMEOUT).to_dict()
    peer_raw = rt.transport.exchange_audit(payload)
    own = audit_records(rt.records)
    opponent = {"passed": False, "verified_steps": 0, "failed_steps": []}
    if peer_raw is not None:
        opponent = audit_records(AuditPayload.from_dict(peer_raw).records)
        if not opponent["passed"] and own["passed"] and rt._result not in _NO_FORFEIT_RESULTS:
            rt._result = "tamper_forfeit_opponent"
    return {"passed": own["passed"] and opponent["passed"], "own": own, "opponent": opponent}


def finish(rt) -> dict:
    """Exchange audits and build the peer's final match summary."""
    audit = exchange_audit(rt)
    summary = {
        "role": "thief",
        "result": rt._result,
        "winner": "thief" if rt._result in (SURVIVAL, "tamper_forfeit_opponent") else "police",
        "records": rt.records,
        "history": rt.handler.history,
        "my_log": list(rt.state.log),
        "disputes": rt.handler.disputes,
        "audit": audit,
        "position": list(rt.state.position),
        "steps": rt.state.step_number,
        "duration_seconds": round(time.monotonic() - rt.started_monotonic, 3),
        "group_id": rt.config.get("game.group_id", "unknown-group"),
        "group_name": rt.config.get("game.group_name", "unnamed"),
        "sub_game_number": rt.sub_game_number,
    }
    rt._notify({"type": "game_over", "summary": summary})
    return summary
